import click
import multiprocessing
import subprocess

N_THREADS = multiprocessing.cpu_count()


def trace_file_len(fname):
    with open(fname) as f:
        for i, l in enumerate(f):
            pass
    return i - 1


def mpirun_cmd(threads, filename):
    return 'mpirun -np %d pb_mpi -cat -gtr -dgam 4 -d %s chain_1' % (threads, filename)


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
def cli(**kwargs):
    """
    FILENAME: the path to the file to process.
    """
    threads = kwargs.get('threads')
    filename = kwargs.get('filename')
    cmd = mpirun_cmd(threads, filename)
    click.echo('Starting run: %s' % cmd)
    # open it in new window and start running
    pid = subprocess.Popen(args=['gnome-terminal', '--command=%s' % cmd]).pid
    print(pid)
