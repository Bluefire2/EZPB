# EZ-PB

Gene tree summary methods are increasingly used to study difficult phylogenetic questions, particularly those that may involve incomplete lineage sorting. Popular programs, such as [ASTRAL](https://github.com/smirarab/ASTRAL) or [ASTRID](https://github.com/pranjalv123/ASTRID), efficiently summarize large numbers of individual gene trees into species trees under the multispecies coalescent model. 

Input gene trees are most conveniently calculated with ML methods, such as [RAxML](https://github.com/stamatak/standard-RAxML) or [IQ-Tree](https://github.com/Cibiv/IQ-TREE). However, there is reason to believe that gene trees obtained from Bayesian Inference are favourable, but they are more challenging to compute.

EZ-PB facilitates the calculation of individual gene trees with the Bayesian package [PhyloBayes](https://github.com/bayesiancook/phylobayes), and its great mixture models. Background on PhyloBayes and its models can be found on the [developers's website](http://www.atgc-montpellier.fr/phylobayes/) and the [Bayesian Kitchen Blog](http://bayesiancook.blogspot.com/).

EZ-PB is an easy-to-use Python wrapper around the PhyloBayes package. As such, EZ-PB does not reconstruct phylogenies itself, but executes the parallel version of [PhyloBayes](https://github.com/bayesiancook/pbmpi) and its diagnostic tools according to specified parameters. Therefore, anyone using EZ-PB must primarily cite the [PhyloBayes authors' research](http://www.atgc-montpellier.fr/phylobayes/paper.php). 

Briefly, EZ-PB executes the following tasks sequentially on each alignment in a set folder: 
  
1. Execute a desired number of chains.
      
2. Automatically check for sufficient sampling and convergence between chains. Convergence criteria are based on the log likelihood effective size, the relative difference in log likelihood, and the maximum difference. Once all of the criteria are satisfied, EZ-PB stops the chains and generates a consensus tree (with bcomp). If chains exceed a certain specified length (the maximum number of generations) without converging, EZ-PB terminates them, in order to prevent any set of chains from running overly too long. All thresholds can be configured.
            
3. Name and organize ‘good’ and ‘bad’ consensus trees and associated analyses files, based upon convergence criteria of the respective chains. Once the above mentioned tasks are completed for a given alignment, the next alignment chains start running.
      
4. Summarize the results in a spreadsheet.

## Installation

1. Make sure that you have Python 3.6+ installed on your machine. If you have multiple versions, you can [create a virtual environment](https://conda.io/docs/user-guide/tasks/manage-environments.html#creating-an-environment-with-commands) with the correct version.
2. Clone the repository using `git`: `git clone https://github.com/Bluefire2/EZPB.git`
3. `cd` into the root directory of the code and run `pip install -e .`.
4. Add the directory to your PATH environment variable. This can be done by adding the following line to your `.bashrc` file: `export PATH="/home/path/to/the/directory:$PATH"
`.
5. Download and compile the current version of [PhyloBayes-MPI](https://github.com/bayesiancook/pbmpi) for your system. After compiling, add the exectuable bpcomp, tracecomp, and pb_mpi into the EZ-PB folder.

Step 4 is not strictly necessary, but it allows you to use the command line interface in any directory, not just the one that the code is in.

## Command line interface
There are two base commands: run and config.

## run
This command runs a set of chains on one or more alignments.

##### Usage
`phylomatic run [OPTIONS] ALIGNMENTS... CHAINS`

ALIGNMENTS: the paths to the alignment files to process. The alignments will be processed sequentially, and not in parallel. To process in parallel, run several instances of this command, adjusting the number of threads accordingly.

Alternatively, any path can be to a directory. In that case, all files of an alignment file type in the directory will be processed sequentially. The file types that the command accepts can be set in the configuration settings.

CHAINS: the number of the chains to run in parallel. Allocated threads will be shared evenly among the chains. The number of chains must be at least two, but cannot be greater than the number of threads allocated.

OPTIONS: the options allow the user to temporarily set variables such as convergence thresholds and the output directory. Alternatively, these can be permanently set with the `config` command. For a detailed list of options and what they do, run `phylomatic run --help`.

##### Output
The default output directory is `phylomatic`. `phylomatic/analyses` will contain a directory for each alignment file, each in turn containing its generated chain files. `phylomatic/good_trees` will contain trees that converged, and `phylomatic/bad_trees` will contain trees that did not (i.e. trees whose chains exceeded the maximum number of generations without converging). Performing a keyboard interrupt (`Ctrl + C`) at any time will stop all currently running chains, and place the currently generated tree in `phylomatic/incomplete_trees`.

## config
This command permanently sets one or more configuration variables.

Alternatively configuration variables can be changed manually by editing `config.ini`.

##### Usage
`phylomatic config [OPTIONS]`

OPTIONS: use these to set a configuration variable, assigning its new value to the option. For a detailed list of options, run `phylomatic config --help`.
