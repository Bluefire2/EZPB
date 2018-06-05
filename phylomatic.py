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

MAX_GEN_DISCARD = int(config['generations']['max_discard'])
MIN_CYCLES = int(config['generations']['min_cycles'])

TRACECOMP_OUT_FILE = config['output']['tracecomp']
LOGLIK_LINE = int(config['output']['loglik_line'])


N_THREADS = multiprocessing.cpu_count()


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
    data = ''  # assume file will have more thant [LOGLIK_LINE] lines
    with open(TRACECOMP_OUT_FILE) as f:
        for i, line in enumerate(f):
            if i == LOGLIK_LINE:
                data = line

    parsed_data = re.sub(r'\s+', ' ', data).split(' ')
    loglik_effsize = int(parsed_data[1])
    loglik_rel_diff = float(parsed_data[2])
    return loglik_effsize, loglik_rel_diff


def check_thresholds(chains, max_gen, max_loglik_size, min_loglik_rel_diff, **thresholds):
    if trace_file_len('%s.trace' % chains[0]) < MIN_CYCLES:
        return True
    else:
        above_max_gen = True
        g = 0
        for chain in chains:
            generations = trace_file_len('%s.trace' % chain)
            print(generations)
            g = generations
            above_max_gen = above_max_gen and (generations > max_gen)

        # we can assume that all the chains have progressed about the same amount, so pick one of the generation values
        discard = min(g / 10, MAX_GEN_DISCARD)
        subprocess.call('./tracecomp -x %d %s' % (discard, ' '.join(chains)),
                        shell=True, stdout=devnull, stderr=devnull)  # suppress output

        # the results get written to a file
        loglik_effsize, loglik_rel_diff = data_from_tracecomp_file()
        print('Log likelihood effective size: %d' % loglik_effsize)
        print('Log likelihood relative difference: %f' % loglik_rel_diff)

        # have the thresholds been broken?
        loglik_effsize_broken = loglik_effsize > max_loglik_size
        loglik_rel_diff_broken = loglik_rel_diff < min_loglik_rel_diff

        thresholds_broken = above_max_gen or (loglik_effsize_broken and loglik_rel_diff_broken)
        return not thresholds_broken


async def check_thresholds_periodic(chains, callback, **thresholds):
    while True:
        if check_thresholds(chains, **thresholds):
            await asyncio.sleep(10)
            continue
        else:
            callback()
            break


def mpirun_cmd(threads, phyle_name, chain_name):
    # Get it? Phyle name? .phy file name?
    return shlex.split('mpirun -np %d pb_mpi -cat -gtr -dgam 4 -d %s %s' % (threads, phyle_name, chain_name))


@click.command()
@click.option('--threads', type=int, default=N_THREADS,
              help='How many threads the process should run on.')
@click.option('--max-gen', type=int, default=30000,
              help='The maximum number of generations to run the process for.')
@click.option('--min-loglik-rel-diff', type=float, default=0.3,
              help='Threshold log likelihood relative difference.')
@click.option('--max-loglik-size', type=int, default=300,
              help='Threshold log likelihood effective size difference.')
@click.option('--min-maxdiff', type=float, default=0.1,
              help='Threshold maximum difference.')
@click.argument('alignment', type=click.Path(exists=True), required=True)
@click.argument('chains', type=str, required=True, nargs=-1)
def cli(threads, alignment, chains, **thresholds):
    """
    ALIGNMENT: the path to the alignmentfile to process.

    CHAINS: the names of the chains to run in parallel. The threads will be shared evenly among the chains. At least two
    chains must be specified.
    """
    if len(chains) < 2:
        print('Error: Must specify at least two chains.')
        sys.exit(1)
    else:
        processes = []
        threads_per_chain = threads / len(chains)
        for chain_name in chains:
            cmd = mpirun_cmd(threads_per_chain, alignment, chain_name)
            click.echo('Starting run: %s' % cmd)
            # open it and start running
            process = subprocess.Popen(cmd)
            processes.append(process)
            print(process)

        def terminate_all():
            for process in processes:
                process.terminate()

        loop = asyncio.get_event_loop()
        loop.run_until_complete(check_thresholds_periodic(list(chains), terminate_all, **thresholds))
