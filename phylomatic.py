import click
import multiprocessing
import subprocess
import asyncio
from contextlib import suppress
import time
import shlex


N_THREADS = multiprocessing.cpu_count()


def trace_file_len(fname):
    try:
        with open(fname) as f:
            for i, l in enumerate(f):
                pass
        return i - 1
    except FileNotFoundError:
        return 0


def check_thresholds(tracefile, max_gen, **thresholds):
    generations = trace_file_len(tracefile)
    # print(generations)
    return generations < max_gen


async def check_thresholds_periodic(tracefile, callback, **thresholds):
    while True:
        if check_thresholds(tracefile, **thresholds):
            await asyncio.sleep(5)
            continue
        else:
            callback()
            break


def mpirun_cmd(threads, filename):
    return shlex.split('mpirun -np %d pb_mpi -cat -gtr -dgam 4 -d %s chain_1' % (threads, filename))


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
@click.argument('filename', type=click.Path(exists=True), required=True)
def cli(threads, filename, **thresholds):
    """
    FILENAME: the path to the file to process.
    """
    cmd = mpirun_cmd(threads, filename)
    click.echo('Starting run: %s' % cmd)
    # open it and start running
    process = subprocess.Popen(cmd)
    print(process)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(check_thresholds_periodic('chain_1.trace', process.terminate, **thresholds))
