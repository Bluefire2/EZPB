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

1. Make sure that you have Python 3.6+ installed on your machine. If you have multiple versions, you can [create a virtual environment](https://conda.io/docs/user-guide/tasks/manage-environments.html#creating-an-environment-with-commands) with the correct version. If you are using conda, you could do `conda create -n ezpb python=3.6`. Once the new environment is set up, activate with `source activate ezpb`.
2. Clone the repository using `git`: `git clone https://github.com/Bluefire2/EZPB.git`
3. Download the current version of [PhyloBayes-MPI](https://github.com/bayesiancook/pbmpi) for your system. You need to copy the exectuables `bpcomp`, `tracecom`p, and `pb_mpi` into the EZPB folder. You may have to compile these for your system.
4. `cd` into the EZPB root directory and run `pip install -e .`.
5. Add the directory to your PATH environment variable. This can be done by adding the following line to your `.bashrc` file: `export PATH="/home/path/to/the/directory:$PATH"`.

Step 5 is not strictly necessary, but it allows you to use the command line interface in any directory, not just the one that the code is in.

## Usage

There is a single basic command for EZ-PB:

`ezpb [OPTIONS] ALIGNMENTS... CHAINS`

ALIGNMENTS: the paths to the alignment files to use. The alignments will be processed sequentially and not in parallel. To process in parallel, run several instances of this command, adjusting the number of threads accordingly (not recommended).

Alternatively, you can provide any path to a directory. In that case, all alignments in that directory will be processed sequentially. PhyloBayes accepts .phylip and .nexus files. EZ-PB is by default set up to use to files ending with .phy, .phylip, or .phylip-relaxed, but .nexus files can also be designated through the config file.

CHAINS: the number of the chains to run in parallel. Allocated threads will be shared evenly among the chains. The number of chains must be at least two, but cannot be greater than the number of threads allocated.

OPTIONS: the options allow the user to temporarily set variables such as convergence thresholds and the output directory. Alternatively, these can be permanently set in the config file. For a detailed list of options and what they do, run `ezpb --help`.

#### Example

If you would like to run PhyloBayes on all alingments in your current directory and use two chain per run, type:

`ezpb . 2`

This invokes 2 chains.

If you would like to run it on a specific folder, type:

`ezpb path/to/folder 2`


##### Output
The default output directory is `ezpb`. `ezpb/analyses` will contain a directory for each alignment file, each in turn containing its generated chain files. `ezpb/good_trees` will contain trees that converged, and `ezpb/bad_trees` will contain trees that did not (i.e. trees whose chains exceeded the maximum number of generations without converging). Performing a keyboard interrupt (`Ctrl + C`) at any time will stop all currently running chains, and place the currently generated tree in `ezpb/incomplete_trees`.

##### Options
If you run EZ-PB on a large number of alignments, the sum of the chain and parameter files will get huge and may clog up your hard drive pretty fast. To overcome this, EZ-PB does by default not save the chain and parameter files of runs that fulfilled the convergence criteria (= the 'good' trees). It only saves the associated files of the 'bad' trees. However, if you would like to keep the chain and parameter files of the good trees as well, simply add the `--save-good-tree-chains` when you start a run: `ezpb . 2 --save-good-tree-chains`.

