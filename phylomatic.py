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

config = configparser.ConfigParser()
config.read('config.ini')

MAX_GEN_DISCARD = int(config['generations']['max_discard'])
MIN_CYCLES = int(config['generations']['min_cycles'])


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


def check_thresholds(chains, max_gen, **thresholds):
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
        # discard = min(g / 10, MAX_GEN_DISCARD)
        # p = subprocess.call('./tracecomp -x %d %s' % (discard, ' '.join(chains)), shell=True)
        # print(p)

        return not above_max_gen


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
@click.option('--max-loglik', type=float, default=0.3,
              help='Threshold log likelihood difference.')
@click.option('--min-size', type=int, default=300,
              help='Threshold effective size difference.')
@click.option('--max-maxdiff', type=float, default=0.1,
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
