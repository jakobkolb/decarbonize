
from pymofa import experiment_handling as eh
from divestcore import divestment_core as model
from X1_visualization import plot_tau_phi, plot_trj_grid
from divestvisuals.data_visualization import plot_trajectories, plot_network, plot_observables, plot_obs_grid

from scipy import interpolate as ip

import numpy as np
import scipy.stats as st
import networkx as nx
import pandas as pd
import cPickle as cp
import itertools as it
import sys
import getpass
import time



def RUN_FUNC(tau, phi, b_r, link_density, N, L, delta_r, delta_c, b_d, filename):
    """
    Set up the model for various parameters and determine
    which parts of the output are saved where.
    Output is saved in pickled dictionaries including the 
    initial values, parameters and consensus state and time 
    for each run.

    Parameters:
    -----------
    tau : float > 0
        the social update timescale
    phi : float \in [0,1]
        the rewiring probability for the network update
    b_r : float
        model parameter:
        prefactor of resource extraction cost
    N : int
        the number of household agents
    L : int
        the initial number of members per household
    delta_r : float
        the resource extraction efficiency for the 
        extraction of the fossil resource in units of
        production_units/resource_uptake^2 to calculate the
        cost of resource extraction:
        cost = delta_r*resource_uptake^2
    delta_c : float \in [0,1)
        capital depreciation rate (is the same in both
        sectors so far)
    b_d : float
        Solov residual for the dirty sector
        should be signifficantly biger than
        for the clean sector (b_c = 1.)
        to ensure higher productivity of the
        fossil sector in the beginning

    """
    #building initial conditions

    while True:
        net = nx.erdos_renyi_graph(N, link_density)
        if len(list(net)) > 1:
            break
    adjacency_matrix = nx.adj_matrix(net).toarray()
    investment_decisions = np.random.randint(low=0, high=2, size=N)
    
    #initializing the model

    m = model.divestment_core(adjacency_matrix, investment_decisions, L, tau, phi)
    m.trajectory_output = False
    m.run_full_time = False
    m.b_r_present = b_r
    m.delta_r_present = delta_r
    m.delta_c = delta_c
    m.b_d = b_d

    #storing initial conditions and parameters

    res = {}
    res["initials"] = \
            pd.DataFrame({"Investment decisions": investment_decisions,
                            "Investment clean": m.investment_clean,
                            "Investment dirty": m.investment_dirty})

    res["parameters"] = \
            pd.Series({ "tau": m.tau,
                        "phi": m.phi,
                        "N": m.N,
                        "birth rate": m.net_birth_rate,
                        "savings rate": m.savings_rate,
                        "clean capital depreciation rate":m.delta_c,
                        "dirty capital depreciation rate":m.delta_d,
                        "resource extraction efficiency":m.delta_r_present,
                        "Solov residual clean":m.b_c,
                        "Solov residual dirty":m.b_d,
                        "pi clean":m.pi,
                        "pi dirty":m.pi,
                        "kappa clean":m.kappa_c,
                        "kappa dirty":m.kappa_d,
                        "rho dirty":m.rho,
                        "initial resource stock":m.R_start})

    #run the model
    
    start = time.clock()
    exit_status = m.run(t_max=300)
    end = time.clock()

    #store exit status

    res["runtime"] = end-start
    res["consensus"] = exit_status

    #store data in case of successful run

    if exit_status in [0,1]:
        print end-start, m.consensus_time, m.tau, m.phi, m.consensus_time/(m.tau*m.phi)
        res["consensus_data"] = \
                pd.DataFrame({"Investment decisions": m.investment_decision,
                            "Investment clean": m.investment_clean,
                            "Investment dirty": m.investment_dirty})
        res["consensus_state"] = m.consensus_state
        res["consensus_time"] = m.consensus_time/m.tau


    #save data
    with open(filename, 'wb') as dumpfile:
        cp.dump(res, dumpfile)
    try:
        tmp = np.load(filename)
    except IOError:
        print "writing results failed for " + filename
    
    return exit_status

def compute(SAVE_PATH_RAW):
    """
    Not quite sure, what this function is good for. 
    copy and pasted it from wbarfuss example experiment.
    I think this could also be accomplished by calling 
    the eh.compute() function directly during the experiment.
    """
    eh.compute(RUN_FUNC, PARAM_COMBS, SAMPLE_SIZE, SAVE_PATH_RAW)

def resave(SAVE_PATH_RAW, SAVE_PATH_RES, sample_size=None):
    """
    dictionary of lambda functions to calculate 
    the average consensus state and consensus time from all
    runs given in the list of filenames (fnames) 
    that is handled internally by resave_data.

    Parameters:
    -----------
    sample_size : int
        the number of runs computed for one 
        combination of parameters e.g. the 
        size of the ensemble for statistical 
        analysis.
    """

    EVA2={  "<mean_consensus_state>":
            lambda fnames: np.nanmean([np.load(f)["consensus_state"] for f in fnames]),
            "<mean_consensus_time>":
            lambda fnames: np.nanmean([np.load(f)["consensus_time"] for f in fnames]),
            "<min_consensus_time>":
            lambda fnames: np.nanmin([np.load(f)["consensus_time"] for f in fnames]),
            "<max_consensus_time>":
            lambda fnames: np.max([np.load(f)["consensus_time"] for f in fnames]),
            "<sem_consensus_time>":
            lambda fnames: st.sem([np.load(f)["consensus_time"] for f in fnames]),
            "<runtime>":
            lambda fnames: st.sem([np.load(f)["runtime"] for f in fnames]),
            }

    eh.resave_data(SAVE_PATH_RAW, PARAM_COMBS, INDEX, EVA2, NAME + '_consensus', sample_size, save_path = SAVE_PATH_RES)


#get subexperiment from comand line
if len(sys.argv)>1:
    sub_experiment = int(sys.argv[1])
else:
    sub_experiment = 0


if getpass.getuser() == "kolb":
    SAVE_PATH_RAW = "/p/tmp/kolb/Divest_Experiments/divestdata/X4/raw_data"
    SAVE_PATH_RES = "/home/kolb/Divest_Experiments/divestdata/X4/results"
elif getpass.getuser() == "jakob":
    SAVE_PATH_RAW = "/home/jakob/PhD/Project_Divestment/Implementation/divestdata/X4/raw_data"
    SAVE_PATH_RES = "/home/jakob/PhD/Project_Divestment/Implementation/divestdata/X4/results"


# Default Experiment tau vs phi for different resource extraction costs
# Raw data generation, post processing and experimental plotting
if sub_experiment == 1:

    SAVE_PATH_RAW = SAVE_PATH_RAW + '_1/'
    SAVE_PATH_RES = SAVE_PATH_RES + '_1/'

    taus = [round(x,5) for x in list(np.linspace(0.,1.,11))[1:-1]]
    phis = [round(x,5) for x in list(np.linspace(0.,1.,11))[1:-1]]
    b_rs = [round(x,5) for x in list(np.linspace(0.,2.,5))[1:-1]]

    N, link_density, L, delta_r, delta_c, b_d = [100], [0.3], [10], [0.01], [1.], [3.]

    PARAM_COMBS = list(it.product(taus,\
        phis, b_rs, link_density, N, L, delta_r, delta_c, b_d))

    NAME = "tau_vs_phi_phase_transition"
    INDEX = {0: "tau", 1: "phi", 2: "b_r"}
    SAMPLE_SIZE = 20

    nodes = 1
    seconds = 2.5 * len(PARAM_COMBS) * SAMPLE_SIZE / nodes
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)
    print len(PARAM_COMBS) * SAMPLE_SIZE
    print 'ETA: %d:%d:%02d' % (d, h, m) 

    compute(SAVE_PATH_RAW)
    resave(SAVE_PATH_RAW, SAVE_PATH_RES, SAMPLE_SIZE)
    plot_tau_phi(SAVE_PATH_RES, NAME+'_consensus')
