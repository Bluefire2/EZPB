import click
import multiprocessing
import subprocess
import asyncio
from contextlib import suppress
import time
import shlex
import sys
from functools import reduce
import configparser
import re
import os

devnull = open(os.devnull, 'w')  # so we can suppress the output of subprocesses

config = configparser.ConfigParser()
config.read('config.ini')

CHECK_FREQ = float(config['default']['check_freq'])

MAX_GEN_DISCARD = int(config['generations']['max_discard'])
MIN_CYCLES = int(config['generations']['min_cycles'])

TRACECOMP_OUT_FILE = config['output']['tracecomp']
LOGLIK_LINE = int(config['output']['loglik_line'])

BPCOMP_OUT_FILE = config['output']['bpcomp']
MAX_DIFF_LINE = int(config['output']['max_diff_line'])

TREE_SAMPLE_FREQ = int(config['default']['tree_sample_freq'])

N_THREADS = multiprocessing.cpu_count()

# CLI defaults:
MAX_GEN = int(config['thresholds']['max_gen'])
MIN_LOGLIK_REL_DIFF = float(config['thresholds']['min_loglik_rel_diff'])
MAX_LOGLIK_EFFSIZE = int(config['thresholds']['max_loglik_effsize'])
MIN_MAXDIFF = float(config['thresholds']['min_maxdiff'])


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


def discard_samples(chain_length):
    return min(chain_length / 10, MAX_GEN_DISCARD)


def check_thresholds(chains, max_gen, max_loglik_effsize, min_loglik_rel_diff, min_maxdiff, **thresholds):
    if trace_file_len('%s.trace' % chains[0]) < MIN_CYCLES:
        return True
    else:
        above_max_gen = True
        g = 0
        for chain in chains:
            generations = trace_file_len('%s.trace' % chain)
            print('Generations for chain %s: %d' % (chain, generations))
            g = generations
            above_max_gen = above_max_gen and (generations > max_gen)

        # we can assume that all the chains have progressed about the same amount, so pick one of the generation values
        discard = discard_samples(g)
        subprocess.call('./tracecomp -x %d %s' % (discard, ' '.join(chains)),
                        shell=True, stdout=devnull, stderr=devnull)  # suppress output

        # the results get written to a file
        loglik_effsize, loglik_rel_diff = data_from_tracecomp_file()
        print('Log likelihood effective size: %d' % loglik_effsize)
        print('Log likelihood relative difference: %f' % loglik_rel_diff)

        # have the thresholds been broken?
        loglik_effsize_broken = loglik_effsize > max_loglik_effsize
        loglik_rel_diff_broken = loglik_rel_diff < min_loglik_rel_diff

        subprocess.call('./bpcomp -x %d %d %s' % (discard, TREE_SAMPLE_FREQ, ' '.join(chains)),
                        shell=True, stdout=devnull, stderr=devnull)  # suppress output

        # once again the results are written to a file
        max_diff = data_from_bpcomp_file()
        print('Max diff: %f' % max_diff)

        # have the thresholds been broken?
        max_diff_broken = max_diff < min_maxdiff

        # print('Thresholds: max loglik %d, min loglik rel diff %f, min maxdiff %f'
        #       % (max_loglik_effsize, min_loglik_rel_diff, min_maxdiff))
        # print('Broken: %d %d %d' % (loglik_effsize_broken, loglik_rel_diff_broken, max_diff_broken))

        thresholds_broken = above_max_gen or (loglik_effsize_broken and loglik_rel_diff_broken and max_diff_broken)
        return not thresholds_broken


async def check_thresholds_periodic(chains, callback, **thresholds):
    while True:
        if check_thresholds(chains, **thresholds):
            await asyncio.sleep(CHECK_FREQ)
            continue
        else:
            callback()
            break


def mpirun_cmd(threads, phyle_name, chain_name):
    # Get it? Phyle name? .phy file name?
    return shlex.split('mpirun -np %d pb_mpi -cat -gtr -dgam 4 -d %s %s' % (threads, phyle_name, chain_name))


def terminate_all_processes(processes):
    for process in processes:
        process.terminate()


@click.command()
@click.option('--threads', type=int, default=N_THREADS,
              help='How many threads the process should run on.')
@click.option('--max-gen', type=int, default=MAX_GEN,
              help='The maximum number of generations to run the process for.')
@click.option('--min-loglik-rel-diff', type=float, default=MIN_LOGLIK_REL_DIFF,
              help='Threshold log likelihood relative difference.')
@click.option('--max-loglik-effsize', type=int, default=MAX_LOGLIK_EFFSIZE,
              help='Threshold log likelihood effective size difference.')
@click.option('--min-maxdiff', type=float, default=MIN_MAXDIFF,
              help='Threshold maximum difference.')
@click.argument('alignments', type=click.Path(exists=True), required=True, nargs=-1)
@click.argument('chains', type=int, required=True)
def cli(threads, alignments, chains, **thresholds):
    """
    ALIGNMENTs: the paths to the alignment files to process. The alignments will be processed sequentially, and not in
    parallel. To process in parallel, run several instances of this command, adjusting the number of threads
    accordingly.

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
        # sequentially process each alignment
        for alignment in alignments:
            processes = []
            threads_per_chain = threads / chains
            alignment_file_name_without_extension = os.path.splitext(alignment)
            # generate some chain names
            chain_names = [('%s_chain_%d' % (alignment_file_name_without_extension[0], j + 1)) for j in range(chains)]
            print('Chains: %s' % ', '.join(chain_names))

            try:
                for chain_name in chain_names:
                    cmd = mpirun_cmd(threads_per_chain, alignment, chain_name)
                    click.echo('Starting run: %s' % ' '.join(cmd))
                    # open it and start running
                    process = subprocess.Popen(cmd)
                    processes.append(process)

                def terminate_all_bound():
                    terminate_all_processes(processes)

                # This event loop blocks execution until it's done, thus preventing the next alignment from being
                # processed until this one is done:
                loop = asyncio.get_event_loop()
                loop.run_until_complete(check_thresholds_periodic(chain_names, terminate_all_bound, **thresholds))

                print('Alignment %s chains finished processing.' % alignment_file_name_without_extension[0])
            except BaseException:  # so that it catches KeyboardInterrupts
                print('Exception raised, terminating all chains...')
                terminate_all_processes(processes)
                raise

            print('All alignment chains finished.')
