
# Copyright (C) 2016-2018 by Jakob J. Kolb at Potsdam Institute for Climate
# Impact Research
#
# Contact: kolb@pik-potsdam.de
# License: GNU AGPL Version 3

try:
    import pickle as cp
except ImportError:
    import pickle as cp
import getpass
import glob
import itertools as it
import sys
import time
import types

import networkx as nx
import numpy as np
import pandas as pd
import scipy.stats as st

from pydivest.divestvisuals.data_visualization \
    import plot_obs_grid, plot_tau_phi, tau_phi_final
from pydivest.micro_model import divestmentcore as model
from pymofa.experiment_handling \
    import experiment_handling, even_time_series_spacing


def RUN_FUNC(tau, phi, eps, N, p, P, b_d, b_R0, e, d_c, test, filename):
    """
    Set up the model for various parameters and determine
    which parts of the output are saved where.
    Output is saved in pickled dictionaries including the 
    initial values, parameters and convergence state and time 
    for each run.

    Parameters:
    -----------
    tau : float > 0
        the social update timescale
    phi : float \in [0,1]
        the rewiring probability for the network update
    eps : float \in [0,1]
        fraction of rewiring and imitation events that 
        are random.
    n : int
        the number of household agents
    L : float \in [0,1]
        connection probability for Erdos
        Renyi random graph
    L : int
        the initial population
    b_d : float
        Solov residual for the dirty sector
        should be signifficantly biger than
        for the clean sector (b_c = 1.)
        to ensure higher productivity of the
        fossil sector in the beginning
    b_R : float
        model parameter:
        pre factor of resource extraction cost
    e   : float
        resource efficiency (output/resource)
    d_c : float \in [0,1)
        capital depreciation rate (is the same in both
        sectors so far)
    test: int \in [0,1]
        wheter this is a test run, e.g.
        can be executed with lower runtime
    filename: string
        filename for the results of the run
    """
    assert isinstance(test, int), \
        'test must be int, is {!r}'.format(test)

    # input parameters

    input_params = {'tau': tau, 'phi': phi, 'eps': eps,
                    'L': P, 'b_d': b_d, 'b_r0': b_R0,
                    'e': e, 'd_c': d_c, 'test': bool(test)}

    # building initial conditions

    while True:
        net = nx.erdos_renyi_graph(N, p)
        if len(list(net)) > 1:
            break
    adjacency_matrix = nx.adj_matrix(net).toarray()
    investment_decisions = np.random.randint(low=0, high=2, size=N)
    
    init_conditions = (adjacency_matrix, investment_decisions)

    # initializing the model

    m = model.DivestmentCore(*init_conditions, **input_params)

    # storing initial conditions and parameters

    res = {
        "initials": pd.DataFrame({"Investment decisions": investment_decisions,
                                  "Investment clean": m.investment_clean,
                                  "Investment dirty": m.investment_dirty}),
        "parameters": pd.Series({"tau": m.tau,
                                 "phi": m.phi,
                                 "n": m.n,
                                 "L": m.P,
                                 "birth rate": m.r_b,
                                 "savings rate": m.s,
                                 "clean capital depreciation rate": m.d_c,
                                 "dirty capital depreciation rate": m.d_d,
                                 "resource extraction efficiency": m.b_r0,
                                 "Solov residual clean": m.b_c,
                                 "Solov residual dirty": m.b_d,
                                 "pi": m.pi,
                                 "kappa_c": m.kappa_c,
                                 "kappa_d": m.kappa_d,
                                 "resource efficiency": m.e,
                                 "epsilon": m.eps,
                                 "initial resource stock": m.G_0})}

    # run the model

    t_max = 300 if test == 0 else 50
    start = time.clock()
    exit_status = m.run(t_max=t_max)

    # store exit status
    res["convergence"] = exit_status
    if test:
        print(m.tau, m.phi, exit_status, \
            m.convergence_state, m.convergence_time)

    # store data in case of successful run

    if exit_status in [0, 1]:
        res["convergence_data"] = \
            pd.DataFrame({"Investment decisions": m.investment_decisions,
                          "Investment clean": m.investment_clean,
                          "Investment dirty": m.investment_dirty})
        res["convergence_state"] = m.convergence_state
        res["convergence_time"] = m.convergence_time

        # interpolate e_trajectory to get evenly spaced time series.
        trajectory = m.e_trajectory
        headers = trajectory.pop(0)

        df = pd.DataFrame(trajectory, columns=headers)
        df = df.set_index('time')
        dfo = even_time_series_spacing(df, 101, 0., t_max)
        res["economic_trajectory"] = dfo

    end = time.clock()
    res["runtime"] = end-start

    # save data
    with open(filename, 'wb') as dumpfile:
        cp.dump(res, dumpfile)
    try:
        tmp = np.load(filename)
    except IOError:
        print("writing results failed for " + filename)
    
    return exit_status


# get sub experiment and mode from command line
if len(sys.argv) > 1:
    input_int = int(sys.argv[1])
else:
    input_int = -1
if len(sys.argv) > 2:
    noise = bool(int(sys.argv[2]))
else:
    noise = True
if len(sys.argv) > 3:
    mode = int(sys.argv[3])
else:
    mode = None

experiments = ['b_d', 'b_R', 'e', 'L', 'test']
sub_experiment = experiments[input_int]
folder = 'X4Noise' if noise else 'X4NoNoise'

# check if cluster or local
if getpass.getuser() == "kolb":
    SAVE_PATH_RAW = "/L/tmp/kolb/Divest_Experiments/divestdata/" \
                    + folder + "/raw_data" + '_' + sub_experiment + '/'
    SAVE_PATH_RES = "/home/kolb/Divest_Experiments/divestdata/" \
                    + folder + "/results" + '_' + sub_experiment + '/'
elif getpass.getuser() == "jakob":
    SAVE_PATH_RAW = \
        "/home/jakob/PhD/Project_Divestment/Implementation/divestdata/" \
        + folder + "/raw_data" + '_' + sub_experiment + '/'
    SAVE_PATH_RES = \
        "/home/jakob/PhD/Project_Divestment/Implementation/divestdata/" \
        + folder + "/results" + '_' + sub_experiment + '/'

taus = [round(x, 5) for x in list(np.linspace(0.0, 1.0, 11))[1:-1]]
phis = [round(x, 5) for x in list(np.linspace(0.0, 1.0, 11))[1:-1]]

b_ds = [round(x, 5) for x in list(1 + np.linspace(0.0, 0.3, 9))]
b_Rs = [round(x, 5) for x in list(10 ** np.linspace(-2.0, 2.0, 5))]
es = [round(x, 5) for x in list(4. ** np.linspace(0.0, 3.0, 4))]
ps = [round(x, 5) for x in list(np.linspace(0.0, 0.3, 7))]
tests = [1]

parameters = {'tau': 0, 'phi': 1, 'eps': 2, 'n': 3, 'L': 4, 'b_d': 5,
              'b_R': 6, 'e': 7, 'd_c': 8, 'test': 9}
tau, phi, eps, N, p, P, b_d, b_R, e, d_c, test = \
    [.8], [.8], [0.0], [100], [0.125], [500], [1.2], [1.], [100], [0.06], [0]
if noise:
    eps = [0.05]

NAME = 'tau_vs_phi_' + sub_experiment + '_sensitivity'
INDEX = {0: "tau", 1: "phi", parameters[sub_experiment]: sub_experiment}

if sub_experiment == 'b_d':
    PARAM_COMBS = list(it.product(taus,
                                  phis, eps, N, p, P, b_ds, b_R, e, d_c, test))

elif sub_experiment == 'b_R':
    PARAM_COMBS = list(it.product(taus, phis, eps, N, p, P, b_d, b_Rs,
                                  e, d_c, test))

elif sub_experiment == 'e':
    PARAM_COMBS = list(it.product(taus, phis, eps, N, p, P, b_d,
                                  b_R, es, d_c, test))

elif sub_experiment == 'L':
    PARAM_COMBS = list(it.product(taus, phis, eps, N, ps, P, b_d,
                                  b_R, e, d_c, test))
    
elif sub_experiment == 'test':
    PARAM_COMBS = list(it.product(taus, phis, eps, N, p, P, b_d,
                                  b_R, e, d_c, tests))


else:
    print(sub_experiment, ' is not in the list of possible experiments')
    sys.exit()

# names and function dictionaries for post processing:

NAME1 = NAME+'_trajectory'
EVA1 = {"<mean_trajectory>":
            lambda fnames: pd.concat([np.load(f)["economic_trajectory"]
                                      for f in fnames]).groupby(
                level=0).mean(),
        "<sem_trajectory>":
            lambda fnames: pd.concat([np.load(f)["economic_trajectory"]
                                      for f in fnames]).groupby(level=0).sem()}

NAME2 = NAME+'_convergence'
EVA2 = {"<mean_convergence_state>":
            lambda fnames: np.nanmean([np.load(f)["convergence_state"]
                                       for f in fnames]),
        "<mean_convergence_time>":
            lambda fnames: np.nanmean([np.load(f)["convergence_time"]
                                       for f in fnames]),
        "<min_convergence_time>":
            lambda fnames: np.nanmin([np.load(f)["convergence_time"]
                                      for f in fnames]),
        "<max_convergence_time>":
            lambda fnames: np.max([np.load(f)["convergence_time"]
                                   for f in fnames]),
        "<nanmax_convergence_time>":
            lambda fnames: np.nanmax([np.load(f)["convergence_time"]
                                      for f in fnames]),
        "<sem_convergence_time>":
            lambda fnames: st.sem([np.load(f)["convergence_time"]
                                   for f in fnames]),
        "<runtime>":
            lambda fnames: st.sem([np.load(f)["runtime"]
                                   for f in fnames]),
        }

# full run
if mode == 0:
    SAMPLE_SIZE = 100
    handle = experiment_handling(SAMPLE_SIZE, PARAM_COMBS, INDEX,
                                 SAVE_PATH_RAW, SAVE_PATH_RES)
    handle.compute(RUN_FUNC)
    handle.resave(EVA1, NAME1)
    handle.resave(EVA2, NAME2)
    plot_tau_phi(SAVE_PATH_RES, NAME2)
    plot_obs_grid(SAVE_PATH_RES, NAME1, NAME2)

# test run
if mode == 1:
    SAMPLE_SIZE = 2
    handle = experiment_handling(SAMPLE_SIZE, PARAM_COMBS, INDEX,
                                 SAVE_PATH_RAW, SAVE_PATH_RES)
    handle.compute(RUN_FUNC)
    handle.resave(EVA1, NAME1)
    handle.resave(EVA2, NAME2)
    plot_tau_phi(SAVE_PATH_RES, NAME2)
    plot_obs_grid(SAVE_PATH_RES, NAME1, NAME2)

# debug and mess around mode:
if mode is None:
    SAMPLE_SIZE = 2
    handle = experiment_handling(SAMPLE_SIZE, PARAM_COMBS, INDEX,
                                 SAVE_PATH_RAW, SAVE_PATH_RES)
    handle.compute(RUN_FUNC)
    handle.resave(EVA1, NAME1)
    handle.resave(EVA2, NAME2)
    plot_tau_phi(SAVE_PATH_RES, NAME2)
    plot_obs_grid(SAVE_PATH_RES, NAME1, NAME2)
