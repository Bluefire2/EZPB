# Phyl-o-matic
--add high-level description here--

This package allows you to run multiple chains on a series of alignment files, sequentially. What this means is that the alignment files are queued up, and as soon as one has finished processing, the next alignment chains start running.

Of course, technically no chain is ever "finished": if left alone, it will run forever. This is the core of Phyl-o-matic: it detects if and when a set of chains converges and stops them, starting the next set.

Convergence criteria are based on the log likelihood effective size, the relative difference in log likelihood, and the maximum difference. Once all of the criteria are satisfied, Phyl-o-matic stops the chains. If the chains get to a certain length (the maximum number of generations) without converging, Phyl-o-matic also stops them, in order to prevent any set of chains from running for too long. All of these thresholds can be configured.

## Output
The default output directory is `phylomatic`. `phylomatic/analyses` will contain a directory for each alignment file, each in turn containing its generated chain files. `phylomatic/good_trees` will contain trees that converged, and `phylomatic_bad_trees` will contain trees that did not (i.e. trees whose chains exceeded the maximum number of generations without converging). Performing a keyboard interrupt (`Ctrl + C`) at any time will stop all currently running chains, and place the currently generated tree in `phylomatic/incomplete_trees`.

## Command line interface
There are two base commands: run and config.

### run
This command runs a set of chains on one or more alignments.

##### Usage
`phylomatic run [OPTIONS] ALIGNMENTS... CHAINS`

ALIGNMENTS: the paths to the alignment files to process. The alignments will be processed sequentially, and not in parallel. To process in parallel, run several instances of this command, adjusting the number of threads accordingly.

Alternatively, any path can be to a directory. In that case, all files of an alignment file type in the directory will be processed sequentially. The file types that the command accepts can be set in the configuration settings.

CHAINS: the number of the chains to run in parallel. Threads will be shared evenly among the chains. The number of chains must be at least two, but cannot be greater than the number of threads allocated.

OPTIONS: the options allow the user to temporarily set variables such as convergence thresholds and the output directory. Alternatively, these can be permanently set with the `config` command. For a detailed list of options and what they do, run `phylomatic run --help`.

### config
This command permanently sets one or more configuration variables.

Alternatively configuration variables can be changed manually by editing `config.ini`.

##### Usage
`phylomatic config [OPTIONS]`

OPTIONS: use these to set a configuration variable, assigning its new value to the option. For a detailed list of options, run `phylomatic config --help`.