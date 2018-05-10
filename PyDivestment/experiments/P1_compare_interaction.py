"""
Compare Trajectory from micro simulation for new and old interaction between households.
"""

import getpass
import itertools as it
import os
import sys
import time

import networkx as nx
import numpy as np
import pandas as pd
from pymofa.experiment_handling import experiment_handling, \
    even_time_series_spacing

from pydivest.micro_model import divestmentcore as micro_model


def RUN_FUNC(interaction, phi, b_d, test):
    """
    Set up the model for various parameters and determine
    which parts of the output are saved where.
    Output is saved in pickled dictionaries including the 
    initial values, parameters and convergence state and time 
    for each run.

    Parameters:
    -----------
    b_d : float > 0
        the solow residual in the dirty sector
    phi : float \in [0,1]
        the rewiring probability for the network update
    approximate: bool
        if True: run macroscopic approximation
        if False: run micro-model
    test: int \in [0,1]
        wheter this is a test run, e.g.
        can be executed with lower runtime
    filename: string
        filename for the results of the run
    """

    # Parameters:

    input_params = {'b_c': 1., 'i_phi': phi, 'i_tau': 1.,
                    'eps': 0.05, 'b_d': b_d, 'e': 100.,
                    'b_r0': 0.1 ** 2 * 100.,
                    'possible_cue_orders': [[0], [1]],
                    'xi': 1. / 8., 'beta': 0.06,
                    'L': 100., 'C': 100., 'G_0': 800.,
                    'campaign': False, 'learning': True,
                    'interaction': interaction, 'test': False}

    # investment_decisions:
    nopinions = [100, 100]

    # network:
    N = sum(nopinions)
    k = 10

    # building initial conditions
    p = float(k) / N
    while True:
        net = nx.erdos_renyi_graph(N, p)
        if len(list(net)) > 1:
            break
    adjacency_matrix = nx.adj_matrix(net).toarray()
    investment_decisions = np.random.randint(low=0, high=2, size=N)

    clean_investment = np.ones(N) * 50. / float(N)
    dirty_investment = np.ones(N) * 50. / float(N)

    init_conditions = (adjacency_matrix, investment_decisions,
                       clean_investment, dirty_investment)

    m = micro_model.DivestmentCore(*init_conditions, **input_params)
    m.init_switchlist()

    # storing initial conditions and parameters

    res = {
        "initials": pd.DataFrame({"Investment decisions": investment_decisions,
                                  "Investment clean": m.investment_clean,
                                  "Investment dirty": m.investment_dirty}),
        "parameters": pd.Series({"tau": m.tau,
                                 "phi": m.phi,
                                 "N": m.n,
                                 "L": m.L,
                                 "savings rate": m.s,
                                 "clean capital depreciation rate": m.d_c,
                                 "dirty capital depreciation rate": m.d_d,
                                 "resource extraction efficiency": m.b_r0,
                                 "Solov residual clean": m.b_c,
                                 "Solov residual dirty": m.b_d,
                                 "pi": m.pi,
                                 "kappa_c": m.kappa_c,
                                 "kappa_d": m.kappa_d,
                                 "xi": m.xi,
                                 "resource efficiency": m.e,
                                 "epsilon": m.eps,
                                 "initial resource stock": m.G_0})}

    # run the model
    t_start = time.clock()

    t_max = 300 if not test else 3
    m.R_depletion = False
    m.run(t_max=t_max)

    t_max += 600 if not test else 6
    m.R_depletion = True
    exit_status = m.run(t_max=t_max)

    res["runtime"] = time.clock() - t_start

    # store data in case of successful run
    if exit_status in [0, 1]:
        # interpolate m_trajectory to get evenly spaced time series.
        df_out = even_time_series_spacing(m.get_mean_trajectory(), 201, 0., t_max)
        df_out.index.name = 'tstep'
    else:
        df_out = None

    return exit_status, df_out


# get sub experiment and mode from command line

# experiment, mode, test

def run_experiment(argv):
    """
    Take arv input variables and run experiment accordingly.
    This happens in five steps:
    1)  parse input arguments to set switches
        for [test, mode, ffh/av, equi/trans],
    2)  set output folders according to switches,
    3)  generate parameter combinations,
    4)  define names and dictionaries of callables to apply to experiment
        data for post processing,
    5)  run computation and/or post processing and/or plotting
        depending on execution on cluster or locally or depending on
        experimentation mode.

    Parameters
    ----------
    argv: list[N]
        List of parameters from terminal input

    Returns
    -------
    rt: int
        some return value to show whether experiment succeeded
        return 1 if sucessfull.
    """
    """
    Get switches from input line in order of
    [test, mode, micro/macro]
    """

    # switch testing mode
    if len(argv) > 1:
        test = bool(int(argv[1]))
    else:
        test = True
    # switch sub_experiment mode
    if len(argv) > 2:
        mode = int(argv[2])
    else:
        mode = 0

    """
    set input/output paths
    """

    respath = os.path.dirname(os.path.realpath(__file__)) + "/../output_data"
    if getpass.getuser() == "jakob":
        tmppath = respath
    elif getpass.getuser() == "kolb":
        tmppath = "/p/tmp/kolb/Divest_Experiments"
    else:
        tmppath = "./"

    folder = 'P1_compare_interaction'

    # make sure, testing output goes to its own folder:

    test_folder = ['', 'test_output/'][int(test)]

    save_path_raw = \
        "{}/{}{}/" \
            .format(tmppath, test_folder, folder)
    save_path_res = \
        "{}/{}{}/" \
            .format(respath, test_folder, folder)

    """
    create parameter combinations and index
    """

    phis = [round(x, 2) for x in list(np.linspace(0.0, 0.9, 20))]
    b_ds = [round(x, 2) for x in list(np.linspace(1., 1.5, 5))]
    interactions = [0, 1, 2]
    b_d, phi, interaction = [1.2, 1.4], [.5, .8], [0, 1, 2]

    if test:
        param_combs = list(it.product(interaction, phi, b_d, [test]))
    else:
        param_combs = list(it.product(interactions, phis, b_ds, [test]))

    """
    run computation and/or post processing and/or plotting
    """
    # Create dummy runfunc output to pass its shape to experiment handle
    params = list(param_combs[0])
    params[-1] = True
    run_func_output = RUN_FUNC(*params)[1]

    sample_size = 100 if not test else 3

    # initialize computation handle
    compute_handle = experiment_handling(run_func=RUN_FUNC,
                                         runfunc_output=run_func_output,
                                         sample_size=sample_size,
                                         parameter_combinations=param_combs,
                                         path_raw=save_path_raw
                                         )

    # define eva functions

    def mean(b_d, phi, interaction, test):

        from pymofa.safehdfstore import SafeHDFStore

        query = 'b_d={} & phi={} & interaction={} & test={}'.format(b_d, phi, interaction, test)

        with SafeHDFStore(compute_handle.path_raw) as store:
            trj = store.select("dat", where=query)

        return -1, trj.groupby(level='tstep').mean()

    def std(b_d, phi, interaction, test):

        from pymofa.safehdfstore import SafeHDFStore

        query = 'b_d={} & phi={} & interaction={} & test={}'.format(b_d, phi, interaction, test)

        with SafeHDFStore(compute_handle.path_raw) as store:
            trj = store.select("dat", where=query)

        return -1, trj.groupby(level='tstep').std()

    eva_1_handle = experiment_handling(run_func=mean,
                                       runfunc_output=run_func_output,
                                       sample_size=1,
                                       parameter_combinations=param_combs,
                                       path_raw=save_path_res + '/mean.h5'
                                       )
    eva_2_handle = experiment_handling(run_func=std,
                                       runfunc_output=run_func_output,
                                       sample_size=1,
                                       parameter_combinations=param_combs,
                                       path_raw=save_path_res + '/std.h5'
                                       )

    if mode == 0:
        # computation, parameters split between threads
        compute_handle.compute()
        return 1
    elif mode == 1:
        # post processing (all parameter combinations on one thread)
        eva_1_handle.compute()
        eva_2_handle.compute()
        return 1
    else:
        # in case nothing happened:
        return 0


if __name__ == "__main__":
    cmdline_arguments = sys.argv
    run_experiment(cmdline_arguments)
