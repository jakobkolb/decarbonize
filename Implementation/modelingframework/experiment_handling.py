"""
This "experiment_handling" (eh) module provides functionality to run a computer
model for various parameter combinations and sample sizes.
@author: wbarfuss
"""
import os
import sys
import glob
import numpy as np
import pandas as pd
import mpi  # wrapper for mpi4py


def compute(run_func, parameter_combinations, sample_size, save_path,
            skipbadruns=False):
    """
    Calls the 'run_func' for several 'parameter_combiantions' and
    'sample_size's and provides a unique ID for each run to store the data at
    the 'save_path' + ID

    Parameters
    ----------
    run_func : function
        The function the executes the model for a given set of parameters.
        The first P paramters need to fit to the parameter_combinations.
        The last parameter of run_func has to be named filename
        If all went well run_func needs to return '1', otherwise another number
    parameter_combinations : list
        A list of tuples of each parameter combination to compute
    sample_size : int
        The size of samples of each parameter combiantion
    save_path : string
        The path to the folder where to store the computed results
    skipbadruns : bool (Default: False)
        If you don't want this function to check for bad runs that shall be
        recalculated, than set to "True". Possible reason: speed.
    """
    # add "/" to save_path if it does not end already with a "/"
    save_path += "/" if not save_path.endswith("/") else ""

    def master():
        if not os.path.exists(save_path):
            os.makedirs(save_path)
        elif skipbadruns:
            badruns = []
        else:
            badruns = find_bad_runs(save_path)

        # preprocessing - Obtaining the data
        tocalc = []
        for s in range(sample_size):
            for p in parameter_combinations:
                if not os.path.exists(save_path + _get_ID(p, s)) or\
                       _get_ID(p, s)[: -4] in badruns:
                    tocalc.append((p, s))

        lentocalc = len(tocalc)
        totallen = len(parameter_combinations) * sample_size
        print ("%i%% already computed" % (100 - (float(lentocalc) * 100 /
                                                 totallen)))
        print str(lentocalc) + " of " + str(totallen) +\
            " single computations left"

        n_nodes = mpi.size - 1
        if n_nodes > 0:
            jobs_per_node = int(lentocalc / n_nodes)
        else:
            jobs_per_node = lentocalc
            n_nodes = 1
        print "Splitting calculations to {} nodes.".format(n_nodes)

        for i in range(n_nodes):
            mpi.submit_call("slave", (tocalc[i*jobs_per_node:
                            (i+1)*jobs_per_node], i), module=__name__)
        if lentocalc > (jobs_per_node * n_nodes):
            mpi.submit_call("slave", (tocalc[(i+1)*jobs_per_node:], i),
                            module=__name__)

    global slave  # slave into the globe scope to work with mpi

    def slave(slavecalcs, sid):
        lentocalc = len(slavecalcs)
        for i, (p, s) in enumerate(slavecalcs):
            _progress_report(i, lentocalc, "computation {} ... ".format(sid))
            exit_status = run_func(*p, filename=save_path + _get_ID(p, s))
            if exit_status != 1:  # Checking for expected execution
                # TODO: proper logging
                print "!!! " + _get_ID(p, s) + " returned with: " \
                    + str(exit_status)

    mpi.run(verbose=0, master_func=master)


def resave_data(source_path, parameter_combinations, index, eva, name,
                sample_size=None, badmisskey=None, save_path=None):
    """
    Resaves the computed "micro" data to smaler files that stores only "macro"
    quanteties of interest. The pickle files are saved in the "data" directory
    at this level of the filesystem tree.

    Parameters
    ----------
    source_path : string
        The path to the folder where the raw computed results are stored
    save_path : string
        The path to the folder where the processed data will be saved.
        If save_path it not given, it defaults to source_path
    parameter_combinations : list
        A list of tuples of each parameter combination to resave
    index : dict as {position at parameter_combination : <name>}
        effective parameter, i.e. the index positions (ints) where they are at
        the complete parameter tuples and their names (strings)
    eva : dict as {<name of macro-quantities> : function how to compute it}
        The function must recieve a list of filenames
    name : string
        The name of the saved macro quantity pickle file
    sample_size : int
        The number of samples to use [Default: None (means: Use all samples)]
    badmisskey : string (optional)
        key that misses in the result dictionaries for badruns (Default: None)
    """
    # add "/" to source_path if it does not end already with a "/"
    source_path += "/" if not source_path.endswith("/") else ""

    # default save_path to source_path if no save_path is given
    if save_path == None:
        save_path = source_path

    # create save_path if it is not yet existing    
    if not os.path.exists(save_path):
        os.makedirs(save_path)

    # Determine bad runs
    badruns = find_bad_runs(source_path, badmisskey)
    print "Badruns:"
    print badruns

    # Determine the maximal sample size to use
    sample_sizes = []
    lenparams = len(parameter_combinations)
    for ip, p in enumerate(parameter_combinations):
        _progress_report(ip, lenparams, "Determine max. sample size... ")
        fnames = np.sort(glob.glob(source_path + _get_ID(p, 0)[:-5] + "*"))
        shortID = fnames[0][fnames[0].rfind("/")+1:fnames[0].rfind("s")]
        NrBadruns = np.sum([badruns[i].startswith(shortID)
                            for i in range(len(badruns))])
        sample_sizes.append(len(fnames)-NrBadruns)
    if sample_size is None:
        # No sample_size given: Using the maximal possible one
        sample_size = int(min(sample_sizes))
        print "Using maximal possible sample size: " + str(sample_size)
    elif sample_size > min(sample_sizes):
        # The data can't provide enough samples for the desired resaving
        raise ValueError("Given sample_size(" + str(sample_size) +
                         ") is too large. Maximal possible sample size: " +
                         str(min(sample_sizes)))
    else:
        # The given sample size can be used
        print "Using sample_size " + str(sample_size) + ". " +\
            "Maximal possible sample size: " + str(min(sample_sizes))

    # Prepare dataframe with multi index
    eff_params = {index[k]: np.unique([p[k] for p in parameter_combinations]) for k in index.keys()}
    mIndex = pd.MultiIndex.from_product(eff_params.values(),
                                        names=eff_params.keys())
    df = pd.DataFrame(index=mIndex)

    # Loop through all parameter combinations
    for i, p in enumerate(parameter_combinations):
        _progress_report(i, lenparams, "Resaving... ")
        fnames = np.sort(glob.glob(save_path + _get_ID(p, 0)[:-5] + "*"))

        # Determine effective filenames (those without the bad_runs)
        badrunmasks = [map(lambda fname: fname.endswith(badrun + ".pkl"),
                           fnames) for badrun in badruns]
        badrunmask = np.zeros(len(fnames))
        for brm in badrunmasks:
            badrunmask = np.logical_or(badrunmask, brm)
        efffnames = np.array(fnames)[np.logical_not(badrunmask)]

        # Set the sample size
        efffnames = np.random.choice(efffnames, size=sample_size)
        # Continue to read the data
        mx = tuple(p[k] for k in index.keys())
        for evakey in eva.keys():
            df.loc[mx, evakey] = eva[evakey](efffnames)


    df.to_pickle(save_path + name)


def find_bad_runs(save_path, missing_key=None):
    """
    Find model runs that did not properly. Such a "bad" run is characterized
    by fewer entries in the saved data dictionary. It is assumend that at least
    one run was not bad, i.e. at least one data dicitonary has more entries
    than bad runs.

    Parameters
    ----------
    save_path : string
        The path to the folder where to store the computed results
    missing_key : string (optional)
        The key of the saved result dictionary that misses in not properly
        computed model runs (Default: None)
        If a missing_key is given, that the number of elements in the saved
        data dictionaries are ignored.

    Returns
    -------
    bad_ones : list
        List of filenames that where did not properly run
    """
    # add "/" to save_path if it does not end already with a "/"
    save_path += "/" if not save_path.endswith("/") else ""
    d = glob.glob("{}*".format(save_path))

    runs = {}
    bad_runs = []
    for i, f in enumerate(d):
        _progress_report(i, len(d), "Collecting bad runs ...")
	ID = f[f.rfind("/")+1:-4]
	try:
		resdic = np.load(f)

		if missing_key is None:
		    runs[ID] = len(resdic)
		elif missing_key not in resdic:
		    bad_runs.append(ID)
	except IOError:
		print "corrupted output in " + f
		bad_runs.append(ID)
    if missing_key is None:
        bad_runs = filter(lambda x: runs[x] < max(runs.values()), runs.keys())

    return bad_runs


def _get_ID(parameter_combination, i):
    """
    Get a unique ID for a 'parameter_combination' and a sample 'i'.

    Parameters
    ----------
    parameter_combination : tuple
        The combination of parameters
    i : int
        The sample

    Returns
    -------
    ID : string
        unique ID plus the ".pkl" ending
    """

    res = str(parameter_combination)  # convert to sting
    res = res[1:-1]  # delete brackets
    res = res.replace(", ", "_")  # replace ", " with "_"
    res = res.replace(".", "o")  # replace dots with an "o"
    res += "_s" + str(i)  # add ensemble index
    res += ".pkl"  # add file type
    return res


def _progress_report(i, loop_length, msg=""):
    """
    A small progress report for a loop of defined length.

    Parameters
    ----------
    i : int
        the current position in the loop
    loop_length : int
        the length of the loop
    msg : string
        (optional) a preceding string
    """
    percent = str(int(np.around(float(i)/loop_length, 2) * 100))
    sys.stdout.write("\r")
    sys.stdout.flush()
    sys.stdout.write(msg + " [" + percent + "%] ")
    sys.stdout.flush()

    if i == loop_length-1:
        sys.stdout.write("\n")
        sys.stdout.flush()
