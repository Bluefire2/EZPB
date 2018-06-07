import click
import multiprocessing
import subprocess
import asyncio
from contextlib import suppress
import time
import shlex
import sys
from functools import reduce, partial
import configparser
import re
import os
from pkg_resources import Requirement, resource_filename
from config import config_types


devnull = open(os.devnull, 'w')  # so we can suppress the output of subprocesses

CONFIG_FILE = resource_filename(Requirement.parse("phyl-o-matic"), "config.ini")
config_data = configparser.ConfigParser()
config_data.read(CONFIG_FILE)

CHECK_FREQ = float(config_data['default']['check_freq'])

MAX_GEN_DISCARD = int(config_data['generations']['max_discard'])
MIN_CYCLES = int(config_data['generations']['min_cycles'])

TRACECOMP_OUT_FILE = config_data['output']['tracecomp']
LOGLIK_LINE = int(config_data['output']['loglik_line'])

BPCOMP_OUT_FILE = config_data['output']['bpcomp']
MAX_DIFF_LINE = int(config_data['output']['max_diff_line'])

TREE_SAMPLE_FREQ = int(config_data['default']['tree_sample_freq'])

N_THREADS = multiprocessing.cpu_count()

# CLI defaults:
MAX_GEN = int(config_data['thresholds']['max_gen'])
MIN_LOGLIK_REL_DIFF = float(config_data['thresholds']['min_loglik_rel_diff'])
MAX_LOGLIK_EFFSIZE = int(config_data['thresholds']['max_loglik_effsize'])
MIN_MAXDIFF = float(config_data['thresholds']['min_maxdiff'])

# Input file types
INPUT_FILE_TYPES = config_data['input']['filetypes'].split(', ')

# Output locations
LOGFILE = 'alignments.log.csv'
TREE_FILE_NAME = 'bpcomp.con.tre'
OUTPUT_DIRECTORY = config_data['output']['directory']

# Output file data
CHAIN_FILE_TYPES = ['.chain', '.monitor', '.param', '.run', '.trace', '.treelist']


def new_tree_file_name(alignment):
    return '%s.tre' % alignment


def every(lst, fn):
    return reduce(lambda acc, elem: acc and fn(elem), lst, True)


def trace_file_len(fname):
    try:
        with open(fname) as f:
            for i, l in enumerate(f):
                pass
        return i - 1
    except FileNotFoundError:
        return 0


def data_from_tracecomp_file():
    data = ''  # assume file will have more thant [MAX_DIFF_LINE] lines
    with open(TRACECOMP_OUT_FILE) as f:
        for i, line in enumerate(f):
            if i == LOGLIK_LINE:
                data = line

    parsed_data = re.sub(r'\s+', ' ', data).split(' ')
    loglik_effsize = int(parsed_data[1])
    loglik_rel_diff = float(parsed_data[2])
    return loglik_effsize, loglik_rel_diff


def data_from_bpcomp_file():
    data = ''  # assume file will have more thant [LOGLIK_LINE] lines
    with open(BPCOMP_OUT_FILE) as f:
        for i, line in enumerate(f):
            if i == MAX_DIFF_LINE:
                data = line

    parsed_data = re.sub(r'\s+', ' ', data).split(' ')
    max_diff = float(parsed_data[2])
    return max_diff


# Precondition: output directory must exist
def create_logfile(output_dir, chains):
    with open(os.path.join(output_dir, LOGFILE), 'w+') as f:
        chain_columns = ', '.join(chains)
        f.write('alignment, converged, loglik_effsize, loglik_rel_diff, max_diff, ' + chain_columns)


# Precondition: logfile must exist
def add_row_to_logfile(output_dir, *args):
    with open(os.path.join(output_dir, LOGFILE), 'a') as f:
        args_as_strings = map(str, args)
        f.write('\n' + ', '.join(args_as_strings))


def discard_samples(chain_length):
    return min(chain_length / 10, MAX_GEN_DISCARD)


# Container class for chain convergence test
class Convergence(object):
    def __init__(self, stop, converged, loglik_effsize, loglik_rel_diff, max_diff, generations):
        self.stop = stop
        self.converged = converged
        self.loglik_effsize = loglik_effsize
        self.loglik_rel_diff = loglik_rel_diff
        self.max_diff = max_diff
        self.generations = generations

    def as_list(self):
        return [self.converged, self.loglik_effsize, self.loglik_rel_diff, self.max_diff]

    def print_data(self):
        for chain, gen in self.generations.items():
            print('Generations for chain %s: %d' % (chain, gen))
        print('Log likelihood effective size: %d' % self.loglik_effsize)
        print('Log likelihood relative difference: %f' % self.loglik_rel_diff)
        print('Max diff: %f' % self.max_diff)


def chain_full_name(alignment, chain):
    return '%s_%s' % (alignment, chain)


def check_thresholds(alignment, chains, min_cycles, max_gen, max_loglik_effsize, min_loglik_rel_diff, min_maxdiff):
    if trace_file_len('%s.trace' % chain_full_name(alignment, chains[0])) < min_cycles:
        return None
    else:
        all_generations = {}
        above_max_gen = True
        g = 0
        for chain in chains:
            generations = trace_file_len('%s.trace' % chain_full_name(alignment, chain))
            all_generations[chain] = generations
            g = generations
            above_max_gen = above_max_gen and (generations > max_gen)

        chain_full_names = [chain_full_name(alignment, chain) for chain in chains]

        # we can assume that all the chains have progressed about the same amount, so pick one of the generation values
        discard = discard_samples(g)
        subprocess.call('tracecomp -x %d %s' % (discard, ' '.join(chain_full_names)),
                        shell=True, stdout=devnull, stderr=devnull)  # suppress output

        # the results get written to a file
        loglik_effsize, loglik_rel_diff = data_from_tracecomp_file()
        # have the thresholds been broken?
        loglik_effsize_broken = loglik_effsize > max_loglik_effsize
        loglik_rel_diff_broken = loglik_rel_diff < min_loglik_rel_diff

        subprocess.call('bpcomp -x %d %d %s' % (discard, TREE_SAMPLE_FREQ, ' '.join(chain_full_names)),
                        shell=True, stdout=devnull, stderr=devnull)  # suppress output

        # once again the results are written to a file
        max_diff = data_from_bpcomp_file()

        # have the thresholds been broken?
        max_diff_broken = max_diff < min_maxdiff

        # print('Thresholds: max loglik %d, min loglik rel diff %f, min maxdiff %f'
        #       % (max_loglik_effsize, min_loglik_rel_diff, min_maxdiff))
        # print('Broken: %d %d %d' % (loglik_effsize_broken, loglik_rel_diff_broken, max_diff_broken))

        converged = loglik_effsize_broken and loglik_rel_diff_broken and max_diff_broken
        stop = above_max_gen or converged
        return Convergence(stop, converged, loglik_effsize, loglik_rel_diff, max_diff, all_generations)


async def check_thresholds_periodic(alignment, chains, callback, check_freq, min_cycles, **thresholds):
    while True:
        result = check_thresholds(alignment, chains, min_cycles, **thresholds)
        # None indicates that the minimum number of cycles has not yet been reached
        if result is None or not result.stop:
            if result is not None:
                # print some data for the user
                result.print_data()
                print('')  # new line

            await asyncio.sleep(check_freq)
            continue
        else:
            # print some data for the user
            result.print_data()
            print('')  # new line
            callback(result)
            break


def mpirun_cmd(threads, phyle_name, chain_name):
    # Get it? Phyle name? .phy file name?
    return shlex.split('mpirun -np %d pb_mpi -cat -gtr -dgam 4 -d %s %s' % (threads, phyle_name, chain_name))


def terminate_all_processes(processes):
    for process in processes:
        process.terminate()


def move_output_files(output_dir, tree_dir, alignment):
    # Create output directory, and subdirectories: analyses, good_trees, bad_trees
    analyses_dir = os.path.join(output_dir, 'analyses', alignment)

    if not os.path.exists(analyses_dir):
        os.makedirs(analyses_dir)

    if not os.path.exists(tree_dir):
        os.makedirs(tree_dir)

    # Move chain files into output/analyses/[alignment]: .chain, .monitor, .param, .run, .trace, .treelist
    for file_type in CHAIN_FILE_TYPES:
        for file in os.listdir('.'):
            if file.endswith(file_type):
                current_path = os.path.join('.', file)
                new_path = os.path.join(analyses_dir, file)
                os.rename(current_path, new_path)

    # Move and rename output tree file
    os.rename(TREE_FILE_NAME, os.path.join(tree_dir, new_tree_file_name(alignment)))


# This is the function that is called when the threshold check fails
def check_fail_callback(convergence, alignment, chains, processes, output_dir):
    # Stop all chain runs
    terminate_all_processes(processes)

    # Write output data to the log
    generations_list = [0 for i in convergence.generations.items()]
    for chain, generations in convergence.generations.items():
        i = chains.index(chain)
        generations_list[i] = generations

    log_data = [alignment] + convergence.as_list() + generations_list
    add_row_to_logfile(output_dir, *log_data)

    # Now we need to move the output files to the correct directories

    # If the chains converged, move the output tree file to good_trees, otherwise move it to bad_trees
    # Also, rename it to [alignment].tre
    if convergence.converged:
        tree_dir = os.path.join(output_dir, 'good_trees')
    else:
        tree_dir = os.path.join(output_dir, 'bad_trees')

    move_output_files(output_dir, tree_dir, alignment)


def apply_decorators(*decorators):
    def decorator(fn):
        for d in reversed(decorators):
            fn = d(fn)
        return fn
    return decorator


@click.group()
def cli():
    pass


@cli.command()
@click.option('--threads', type=int, default=N_THREADS,
              help='How many threads the process should run on. Default: %d.' % N_THREADS)
@click.option('--max-gen', type=int, default=MAX_GEN,
              help='The maximum number of generations to run the process for. Default: %d.' % MAX_GEN)
@click.option('--min-loglik-rel-diff', type=float, default=MIN_LOGLIK_REL_DIFF,
              help='Threshold log likelihood relative difference. Default: %f.' % MIN_LOGLIK_REL_DIFF)
@click.option('--max-loglik-effsize', type=int, default=MAX_LOGLIK_EFFSIZE,
              help='Threshold log likelihood effective size difference. Default: %d.' % MAX_LOGLIK_EFFSIZE)
@click.option('--min-maxdiff', type=float, default=MIN_MAXDIFF,
              help='Threshold maximum difference. Default: %f.' % MIN_MAXDIFF)
@click.option('--check-freq', type=float, default=CHECK_FREQ,
              help='How often to check for convergence (in seconds). Default: %f.' % CHECK_FREQ)
@click.option('--min-cycles', type=int, default=MIN_CYCLES,
              help='How many generations to ignore before checking for convergence. Default: %d.' % MIN_CYCLES)
@click.option('--out', type=str, default=OUTPUT_DIRECTORY,
              help='The directory to store the output files in. Default: %s.' % OUTPUT_DIRECTORY)
@click.argument('alignments', type=click.Path(exists=True), required=True, nargs=-1)
@click.argument('chains', type=int, required=True)
def run(threads, alignments, chains, check_freq, min_cycles, out, **thresholds):
    """
    ALIGNMENTS: the paths to the alignment files to process. The alignments will be processed sequentially, and not in
    parallel. To process in parallel, run several instances of this command, adjusting the number of threads
    accordingly.

    Alternatively, the paths can be to directories. In that case, all files of the relevant file type in the directory
    will be processed sequentially. The file types that the command accepts can be set in the configuration file.

    CHAINS: the number of the chains to run in parallel. Threads will be shared evenly among the chains. The number of
    chains must be at least two, but cannot be greater than the number of threads allocated.
    """
    if chains < 2:
        print('Error: Must specify at least two chains.')
        sys.exit(1)
    elif chains > threads:
        print('Error: The number of chains cannot be less than the number of threads allocated.')
        sys.exit(1)
    else:
        # generate some chain names
        chain_names = [('chain_%d' % (j + 1)) for j in range(chains)]
        print('Chains: %s' % ', '.join(chain_names))
        # create the output directory
        os.mkdir(out)
        # create a logfile
        create_logfile(out, chain_names)

        alignment_files = []
        for path in alignments:
            if os.path.isfile(path):
                alignment_files.append(path)
            else:
                for file in os.listdir(path):
                    for file_type in INPUT_FILE_TYPES:
                        if file.endswith(file_type):
                            alignment_files.append(file)

        # sequentially process each alignment
        for alignment in alignment_files:
            processes = []
            threads_per_chain = threads / chains
            alignment_file_name_without_extension = os.path.splitext(alignment)[0]

            # generate specific chain file names
            chain_full_names = [chain_full_name(alignment_file_name_without_extension, chain_name)
                                for chain_name in chain_names]

            try:
                for chain_name in chain_full_names:
                    cmd = mpirun_cmd(threads_per_chain, alignment, chain_name)
                    click.echo('Starting run: %s' % ' '.join(cmd))
                    # open it and start running
                    process = subprocess.Popen(cmd)
                    processes.append(process)

                callback = partial(check_fail_callback,
                                   alignment=alignment_file_name_without_extension,
                                   chains=chain_names,
                                   processes=processes,
                                   output_dir=out)

                # This event loop blocks execution until it's done, thus preventing the next alignment from being
                # processed until this one is done:
                loop = asyncio.get_event_loop()
                loop.run_until_complete(check_thresholds_periodic(
                    alignment_file_name_without_extension, chain_names, callback, check_freq, min_cycles, **thresholds))

                print('Alignment %s chains finished processing.' % alignment_file_name_without_extension)
            except BaseException:  # so that it catches KeyboardInterrupts
                # Upon an exception:
                # 1. Stop all chains
                # 2. Move all chain output files to output/analyses
                # 3. Move output tree file to output/terminated_trees

                # Step 1:
                print('Exception raised, terminating all chains...')
                terminate_all_processes(processes)

                # Steps 2 & 3:
                print('Saving output files...')
                tree_dir = os.path.join(out, 'terminated_trees')
                move_output_files(out, tree_dir, alignment)
                raise

            print('All alignment chains finished.')


config_cmd_decorators = []
for category, variables in config_data.items():
    for variable, value in variables.items():
        full_variable_name = '%s-of-%s' % (variable, category)
        current_value = config_data[category][variable]
        decorator = click.option(
            '--%s' % full_variable_name,
            type=config_types[category][variable],
            default=None,
            help='Set the configuration variable %s. Current value: %s.' % (full_variable_name, current_value)
        )
        config_cmd_decorators.append(decorator)


@cli.command()
@apply_decorators(*config_cmd_decorators)
def config(**config_variables):
    for var, val in config_variables.items():
        if val is not None:
            name, cat = var.split('_of_')
            config_data[cat][name] = val

    with open(CONFIG_FILE, 'w') as configfile:
        config_data.write(configfile)
