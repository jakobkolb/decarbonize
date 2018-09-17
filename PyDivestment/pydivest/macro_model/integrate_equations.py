"""Naming convention: p_ precedes parameter names, and v_precedes variable names"""

import sys

import numpy as np
import sympy as sp
import pandas as pd


class IntegrateEquations:
    """Parent class for macro approximation modules.

    All definitions that are universal to the different approximations are class variables.
    """

    from sympy.abc import epsilon, phi, tau

    # Define variables and parameters for the adaptive voter model

    # number of nodes
    N = sp.Symbol('N', integer=True)
    # number of dirty nodes
    Nd = sp.Symbol('N_d', integer=True)
    # number of clean nodes
    Nc = sp.Symbol('N_c', integer=True)
    # number of edges
    K = sp.Symbol('K', integer=True)
    # number of clean edges
    cc = sp.Symbol('[cc]', integer=True)
    # number of dirty edges
    dd = sp.Symbol('[dd]', integer=True)
    # number of mixed edges
    cd = sp.Symbol('[cd]', integer=True)
    # average number of neighbors of clean nodes
    kc = sp.Symbol('k_c', integer=True)
    # average number of neighbors of dirty nodes
    kd = sp.Symbol('k_d', integer=True)
    # Nc - Nd
    X = sp.Symbol('X', real=True)
    # cc - dd
    Y = sp.Symbol('Y', real=True)
    # cd
    Z = sp.Symbol('Z', real=True, positive=True)
    # wealth of dirty node
    Wd = sp.Symbol('W_d')
    # wealth of clean node
    Wc = sp.Symbol('W_c')
    # imitation probabilities
    Pcd, Pdc = sp.symbols('Pcd Pdc')

    # rescaled variables for PBP approximation

    x, y, z, k = sp.symbols('x y z k')
    c, g, p, g0 = sp.symbols('c, g, p, g_0')

    # Define variables and parameters for the economic subsystem:

    P, Pc, Pd = sp.symbols('P P_c P_d', positive=True, real=True)
    Kc, Kd = sp.symbols('K_c K_d', positive=True, real=True)
    w, rc, rd = sp.symbols('w r_c r_d', positive=True, real=True)
    R, G, C = sp.symbols('R, G, C', positive=True, real=True)
    rs, delta, pi, kappac, kappad, xi = sp.symbols('s delta pi kappa_c, kappa_d xi', positive=True, rational=True,
                                                   real=True)
    bc, bd, bR, e, G0 = sp.symbols('b_c b_d b_R e G_0', positive=True, real=True)
    Xc, Xd, XR = sp.symbols('X_c X_d X_R', positive=True, real=True)

    # Defination of relations between variables and calculation of substitution of
    # *primitive variables* by *state variables* of the system

    eqs = [
        Nd + Nc - N,
        cc + dd + cd - K,
        X - Nc + Nd,
        Y - cc + dd,
        Z - cd,
        kc - (2 * cc + cd) / Nc,
        kd - (2 * dd + cd) / Nd
    ]
    vars1 = (Nc, Nd, cc, dd, cd, kc, kd)
    vars2 = (N, K, X, Y, Z)
    subs1 = sp.solve(eqs, vars1, dict=True)[0]

    # Effect of events on state vector S = (X, Y, Z)

    # regular adaptive voter events
    s1 = sp.Matrix([0, 1, -1])  # clean investor rewires
    s2 = sp.Matrix([0, -1, -1])  # dirty investor rewires
    s3 = sp.Matrix([-2, -kc, -1 + (1 - 1. / kc) * ((2 * cc - cd) / Nc)])  # clean investor imitates c -> d
    s4 = sp.Matrix([2, kd, -1 + (1 - 1. / kd) * ((2 * dd - cd) / Nd)])  # dirty investor imitates d -> c

    # noise events
    s5 = sp.Matrix([-2, -(2 * cc + cd) / Nc, (2 * cc - cd) / Nc])  # c -> d
    s6 = sp.Matrix([2, (2 * dd + cd) / Nd, (2 * dd - cd) / Nd])  # d -> c
    s7 = sp.Matrix([0, -1, 1])  # c-c -> c-d
    s8 = sp.Matrix([0, 1, -1])  # c-d -> c-c
    s9 = sp.Matrix([0, 1, 1])  # d-d -> d-c
    s10 = sp.Matrix([0, -1, -1])  # d-c -> d-d

    # Probabilities for events to occur:

    # Regular Events
    p1 = (1 - epsilon) * phi * (Nc / N) * cd / (Nc * kc)  # clean investor rewires
    p2 = (1 - epsilon) * phi * (Nd / N) * cd / (Nd * kd)  # dirty investor rewires
    p3 = (1 - epsilon) * (1 - phi) * (Nc / N) * cd / (Nc * kc) * Pcd  # clean investor imitates c -> d
    p4 = (1 - epsilon) * (1 - phi) * (Nd / N) * cd / (Nd * kd) * Pdc  # dirty investor imitates d -> c

    # Noise Events
    p5 = epsilon * (1 - phi) * (1. / 2) * Nc / N  # imitation noise c -> d
    p6 = epsilon * (1 - phi) * (1. / 2) * Nd / N  # imitation noise d -> c
    p7 = epsilon * phi * Nc / N * (2 * cc) / (2 * cc + cd) * Nd / N  # rewiring noise c-c -> c-d
    p8 = epsilon * phi * Nc / N * cd / (2 * cc + cd) * Nc / N  # rewiring noise c-d -> c-c
    p9 = epsilon * phi * Nd / N * (2 * dd) / (2 * dd + cd) * Nc / N  # rewiring noise d-d -> d-c
    p10 = epsilon * phi * Nd / N * cd / (2 * dd + cd) * Nd / N  # rewiring noise d-c -> d-d

    # Switching terms for economic subsystem (total rate of households
    # changing from clean to dirty investment and vice versa)
    dtNcd = N / tau * (p3 + p5)
    dtNdc = N / tau * (p4 + p6)

    # Create S and r matrices to write down rhs markov jump process for pair based proxy:

    S = sp.Matrix(s1)
    for i, si in enumerate([s2, s3, s4, s5, s6, s7, s8, s9, s10]):
        S = S.col_insert(i + 1, si)

    r = sp.Matrix([p1])
    for j, pj in enumerate([sp.Matrix([p]) for p in [p2, p3, p4, p5, p6, p7, p8, p9, p10]]):
        r = r.col_insert(j + 1, pj)

    rhsPBP = S * sp.Transpose(r)

    # Write down right hand side for PBP and substitute primitive with system state variables:

    rhsPBP = 1. / tau * rhsPBP.subs(subs1)

    # Solutions to the algebraic constraints from labor and capital markets

    subs2 = {w: pi * P ** (pi - 1) * (Xc + Xd * XR) ** (1 - pi),
             rc: kappac / Kc * Xc * P ** pi * (Xc + Xd * XR) ** (-pi),
             rd: kappad / Kd * Xd * XR * P ** pi * (Xc + Xd * XR) ** (-pi),
             R: bd / e * Kd ** kappad * P ** pi * (Xd * XR / (Xc + Xd * XR)) ** pi,
             Pc: P * Xc / (Xc + Xd * XR),
             Pd: P * Xd * XR / (Xc + Xd * XR),
             }

    subs3 = {Xc: (bc * Kc ** kappac * C ** xi) ** (1. / (1 - pi)),
             Xd: (bd * Kd ** kappad) ** (1. / (1 - pi)),
             XR: (1. - bR / e * (G0 / G) ** 2) ** (1. / (1 - pi))}

    # Define lists of symbols for parameters to substitute in rhs expression
    param_symbols = [bc, bd, bR, e, rs, delta, pi, kappac, kappad, xi, g0, p, G0, P,
                     epsilon, phi, tau, k, N]

    def __init__(self, adjacency=None, investment_decisions=None,
                 investment_clean=None, investment_dirty=None,
                 tau=0.8, phi=.7, eps=0.05,
                 pi=0.5, kappa_c=0.4, kappa_d=0.5, xi=1. / 8.,
                 L=100., b_c=1., b_d=1.5, s=0.23, d_c=0.06,
                 b_r0=1., e=10, G_0=3000, C=1,
                 R_depletion=True, test=False, crs=True, interaction=1,
                 **kwargs):
        """
        Handle the parsing of parameters for the approximation modules.

        Parameters
        ----------
        adjacency: np.ndarray
            Acquaintance matrix between the households. Has to be symmetric unweighted and without self loops.
        investment_decisions: iterable[int]
            Initial investment decisions of households. Will be updated
            from their actual heuristic decision making during initialization
        investment_clean: iterable[float]
            Initial household endowments in the clean sector
        investment_dirty: iterable[float]
            Initial household endowments in the dirty sector
        tau: float
            Mean waiting time between household opinion updates
        phi: float
            Rewiring probability in the network adaptation process
        eps: float
            fraction of exploration events (noise) in the opinion formation process
        b_c: float
            Solow residual of the production function of the clean sector
        b_d: float
            Solow residual of the production function of the dirty sector
        s: float
            Savings rate of the households
        d_c: float
            Capital depreciation rate
        b_r0: float
            Resource cost factor
        e: float
            Resource efficiency in the dirty sector
        pi: float
            labor elasticity for both sectors
        kappa_c: float
            capital elasticity for the clean sector
        kappa_d: float
            capital elasticity for the dirty sector
        xi: float
            elasticity of the knowledge stock in the clean sector
        L: float
            Total labor (fixed)
        G_0: float
            Total initial resource stock
        C: float
            Total initial knowledge stock
        resource_depletion: bool
            Switch to turn resource depreciation on or off
        interaction: int
            Switch for different imitation probabilities.
            if 0: tanh(Wi-Wj) interaction,
            if 1: interaction as in Traulsen, 2010 but with relative differences
            if 2: (Wi-Wj)/(Wi+Wj) interaction.
        crs: bool
            switch for constant returns to scale. If True, values of kappa are ignored.
        test: bool
            switch on debugging options
        """

        # ----------------------------------------------------------------------------------------------------
        # Parse Parameters
        # ----------------------------------------------------------------------------------------------------

        self.p_test = test
        self.p_crs = crs
        self.p_interaction = interaction

        # Social parameters

        # mean waiting time between social updates
        self.p_tau = float(tau)
        # rewiring probability for adaptive voter model
        self.p_phi = float(phi)
        # percentage of rewiring and imitation events that are noise
        self.p_eps = float(eps)
        # number of households (to interface with initial
        # conditions from micro model)
        self.p_n = float(adjacency.shape[0])
        # mean degree
        self.p_k = float(sum(sum(adjacency))) / self.p_n / 2.
        # investment_decisions as indices of possible_que_orders
        self.investment_decisions = np.array(investment_decisions)

        # Sector parameters

        # Clean capital depreciation rate
        self.p_d_c = float(d_c)
        # Dirty capital depreciation rate
        self.p_d_d = float(self.p_d_c)
        # knowledge depreciation rate
        self.p_beta = float(self.p_d_c)
        # Resource harvest cost per unit (at full resource stock)
        self.p_b_r0 = float(b_r0)
        # percentage of income saved
        self.p_s = float(s)
        # solow residual for clean sector
        self.p_b_c = float(b_c)
        # solow residual for dirty sector
        self.p_b_d = float(b_d)
        # elasticity of knowledge
        self.p_xi = float(xi)
        # labor elasticity (equal in both sectors)
        self.p_pi = pi
        # clean capital elasticity
        # clean and dirty capital elasticity
        if crs:
            self.p_kappa_c = 1. - self.p_pi - self.p_xi
            self.p_kappa_d = 1. - self.p_pi
        else:
            self.p_kappa_c = float(kappa_c)
            self.p_kappa_d = float(kappa_d)
        if self.p_test:
            print('pi = {}, xi = {}, kappa_c = {}, kappa_d = {}'.format(self.p_pi, self.p_xi,
                                                                        self.p_kappa_c, self.p_kappa_d), flush=True)
        # fossil->energy->output conversion efficiency (Leontief)
        self.p_e = float(e)
        # total labor
        self.p_P = float(L)
        # labor per household
        self.p_l = float(L) / self.p_n
        # total knowledge stock
        self.v_C = float(C)
        # unprofitable fraction of fossil reserve
        self.p_alpha = (b_r0 / e) ** 0.5

        # Ecosystem parameters

        # initial fossil resource stock
        self.p_G_0 = float(G_0)
        # total fossil resource stock
        self.v_G = float(G_0)
        # initial fossil resource stock per household
        self.p_g_0 = float(G_0) / self.p_n
        # toggle resource depletion
        self.R_depletion = R_depletion

        # system time
        self.v_t = 0
        self.p_t_max = 0

        # ----------------------------------------------------------------------------------------------------
        # Parse Initial Conditions
        # ----------------------------------------------------------------------------------------------------

        # household investment in dirty capital
        if investment_dirty is None:
            self.investment_dirty = np.ones(self.p_n)
        else:
            self.investment_dirty = investment_dirty

        # household investment in clean capital
        if investment_clean is None:
            self.investment_clean = np.ones(self.p_n)
        else:
            self.investment_clean = investment_clean

        # system variables and their initial values
        def cl(adj, x, y):
            """
            calculate number of links between like links in x and y
            :param adj: adjacency matrix
            :param x: node vector
            :param y: node vector
            :return: number of like links
            """
            assert len(x) == len(y)

            n = len(x)
            ccc = 0

            for i in range(n):
                for j in range(n):
                    ccc += x[i] * adj[i, j] * y[j]

            return float(ccc)

        adj = adjacency
        c = self.investment_decisions
        d = - self.investment_decisions + 1

        cc = cl(adj, c, c) / 2
        cd = cl(adj, c, d)
        dd = cl(adj, d, d) / 2

        n = len(c)
        k = float(sum(sum(adj))) / 2

        nc = sum(c)
        nd = sum(d)

        self.v_x = float(nc - nd) / n
        self.v_y = float(cc - dd) / k
        self.v_z = float(cd) / k

        self.v_c = float(self.v_C) / n
        self.v_g = self.p_g_0

        # define dictionary of substitutions for rescalled variables as instance property, since different
        # subclasses are extending it differently.

        self.subs4 = {self.Kc: 'I am a placeholder',
                      self.Kd: 'I am a placeholder',
                      self.X: self.N * self.x,
                      self.Y: self.N * self.k * self.y,
                      self.Z: self.N * self.k * self.z,
                      self.K: self.N * self.k}

        # Define interaction terms depending on value of interaction.
        # Interaction terms are given by the expected value of the
        # micro interaction terms which is calculated by taking the expected value
        # of their taylor expansion up to linear terms. The expansion is done around
        # half of the capital values that would be expected for full clean and full dirty
        # economy respectively, hoping to get a decent approximation in the entire
        # reachable phase space.

        # equilibrium clean capital in full clean economy:
        Kc_star = (self.rs **(1 - self.xi)
                   * self.bc/self.delta
                   * self.P**self.pi
                   )**(1./(1.-self.kappac - self.xi))
        # equilibrium knowledge stock in full clean economy:
        C_star = (self.rs**self.kappac
                  * self.bc/self.delta
                  * self.P**self.pi
                  )**(1./(1. - self.kappac - self.xi))
        # equilibrium dirty capital in full dirty economy:
        Kd_star = (self.rs * self.bc/self.delta
                   * (1. - self.bR/self.e)
                   * (self.kappad + self.pi)
                   * self.P**self.pi
                   )**(1./(1 - self.kappad))

        # expected income in full clean and full dirty economy

        # Wd* = w P + r_c * K_c*
        Wd_star = self.bd * (self.kappad + self.pi) * (1. - self.bR/self.e) * self.P ** self.pi * Kd_star ** self.kappad
        # Wd* = w P + r_d * K_d*
        Wc_star = self.bc * (self.kappac + self.pi) * self.P**self.pi * Kc_star**self.kappac * C_star**self.xi

        # normalized difference in clean and dirty income for half of the max expected income:
        Wcd_star = (Wc_star - Wd_star)/(Wc_star + Wd_star)
        Wdc_star = (Wd_star - Wc_star)/(Wc_star + Wd_star)

        Wij0, Wji0, Wi0, Wj0, Wi, Wj = sp.symbols('W_ij0 W_ji0 W_i0 W_j0 Wi Wj')

        if interaction == 0:
            self.subs1[self.Pcd] = (1./2.*(self.Wd - self.Wc + 1))
            self.subs1[self.Pdc] = (1./2.*(self.Wc - self.Wd + 1))
        elif interaction == 1:
            # write down taylor expansion of Pcd = 1/(1+exp(8(Wc - Wd)/(Wc + Wd)))
            Pij = (1. / (1 + sp.exp(8. * Wij0)))
            diPij = - sp.exp(8. * Wij0) / (1. + sp.exp(8. * Wij0))**2. * 16. * Wj0 / (Wi0 + Wj0) ** 2.
            djPij =   sp.exp(8. * Wij0) / (1. + sp.exp(8. * Wij0))**2. * 16. * Wi0 / (Wi0 + Wj0) ** 2.
            texpPij = Pij + diPij * (Wi - Wi0/2.) + djPij * (Wj - Wj0/2.)
            icjd = {Wij0: Wcd_star, Wi0: Wc_star, Wj0: Wd_star, Wi: self.Wc, Wj: self.Wd}
            idjc = {Wij0: Wdc_star, Wi0: Wd_star, Wj0: Wc_star, Wi: self.Wd, Wj: self.Wc}
            self.subs1[self.Pcd] = texpPij.subs(icjd)
            self.subs1[self.Pdc] = texpPij.subs(idjc)
            # Old:
            # self.subs1[self.Pcd] = 1./(1 + sp.exp(- 8. * (self.Wd - self.Wc)/(self.Wc + self.Wd)))
            # self.subs1[self.Pdc] = 1./(1 + sp.exp(- 8. * (self.Wc - self.Wd)/(self.Wc + self.Wd)))
        elif interaction == 2:
            self.subs1[self.Pcd] = ((1. / 2.) * ((self.Wd - self.Wc) / (self.Wd + self.Wc) + 1.))
            self.subs1[self.Pdc] = ((1. / 2.) * ((self.Wc - self.Wd) / (self.Wd + self.Wc) + 1.))
        else:
            raise ValueError('interaction must be in [0, 1, 2] but is {}'.format(interaction))

        # Define list of dependent and independent variables to calculate and save their values.
        self.independent_vars = {'x': self.x, 'y': self.y, 'z': self.z}
        # Define list of dependent and independent variables to calculate and save their values.
        self.dependent_vars_raw = {'w': self.w, 'rc': self.rc, 'rd': self.rd,
                                   'R': self.R, 'Kd': self.Kd, 'Kc': self.Kc,
                                   'Lc': self.Pc, 'Ld': self.Pd, 'L': self.P, 'rs': self.rs,
                                   'W_d': self.Wd, 'W_c': self.Wc, 'Pcd': self.Pcd, 'Pdc': self.Pdc,
                                   'l': self.p, 'Nc': self.Nc, 'Nd': self.Nd, 'P': self.P}

        # Some dummy attributes to be specified by child classes.
        self.rhs_raw = None
        self.rhs = None
        self.rhs_func = None
        self.param_values = []
        self.subs_params = {}
        self.dependent_vars = {}
        self.var_symbols = []

    def update_dependent_vars(self):

        if self.p_test:
            print('updating dependent variables')

        # Add new variables to list of independent Variables.
        for key, val in zip(self.var_names, self.var_symbols):
            self.independent_vars[key] = val

        # Substitute expressions in variables
        for key in self.dependent_vars_raw.keys():
            self.dependent_vars_raw[key] = self.dependent_vars_raw[key].subs(self.subs1)\
                .subs(self.subs2).subs(self.subs3) \
                .subs(self.subs1).subs(self.subs4).subs({self.N: 1})

    def list_parameters(self):
        # link parameter symbols to values,
        self.param_values = [self.p_b_c, self.p_b_d, self.p_b_r0, self.p_e, self.p_s, self.p_d_c, self.p_pi,
                             self.p_kappa_c, self.p_kappa_d, self.p_xi, self.p_g_0, self.p_l, self.p_G_0, self.p_P,
                             self.p_eps, self.p_phi, self.p_tau, self.p_k, 1.]

        return {symbol: value for symbol, value in zip(self.param_symbols, self.param_values)}

    def set_parameters(self):
        """(re)set parameter values in rhs and dependent expressions"""

        self.subs_params = self.list_parameters()

        if self.p_test:
            print('resetting parameter values to')
            print(self.subs_params)

        # replace parameter symbols in raw rhs,
        self.rhs = self.rhs_raw.subs(self.subs_params)

        # lambdify rhs expressions for faster evaluation in integration
        self.rhs_func = [sp.lambdify(tuple(self.var_symbols), r_i) for r_i in self.rhs]

        # replace parameter symbols in raw independent variables.
        for key in self.dependent_vars_raw.keys():
            self.dependent_vars[key] = self.dependent_vars_raw[key].subs(self.subs_params)
        if self.p_test:
            print('sucessfull')



    def dot_rhs(self, values, t):
        """
        Evaluate the right hand side of the system given the values of the independent variables
        Parameters
        ----------
        values: list[float]
            values of independent variables
        t: float
            system time

        Returns
        -------
        rval: list[float]
            value of right hand side
        """

        if self.p_test:
            self.progress(t, self.p_t_max, 'mean approximation running')

        # add to g such that 1 - alpha**2 * (g/G_0)**2 remains positive
        if values[-1] < self.p_alpha * self.p_g_0:
            values[-1] = self.p_alpha * self.p_g_0

        # use original sympy expressions for integration

        # Use lambdified expressions for integration
        rval = [rhs_i(*values) for rhs_i in self.rhs_func]

        # for constant resource set g_dot to zero
        if not self.R_depletion:
            rval[-1] = 0
        return rval

    @staticmethod
    def progress(count, total, status=''):
        bar_len = 60
        filled_len = int(round(bar_len * count / float(total)))

        percents = round(100.0 * count / float(total), 1)
        bar = '=' * filled_len + '-' * (bar_len - filled_len)

        sys.stdout.write('[%s] %s%s ...%s\r' % (bar, percents, '%', status))
        sys.stdout.flush()

    def calculate_unified_trajectory(self, columns, var_expressions):
        """
        Calculate the values of unified output variables from given expressions
        Parameters
        ----------
        columns: iterable[string]
            names of the output variables
        var_expressions: iterable
            sympy expressions for output variables

        Returns
        -------
        df_out: pd.DataFrame
            Dataframe with timestamps t as index, variable names as columns
            and variable values at times t as content

        """

        t_values = self.m_trajectory.index.values
        data = np.zeros((len(t_values), len(columns)))
        var_expressions_lambdified = [sp.lambdify(tuple(self.var_symbols), expr)
                                      for expr in var_expressions]
        for i, t in enumerate(t_values):
            if self.p_test:
                self.progress(i, len(t_values), 'calculating dependant variables')
            Yi = self.m_trajectory.loc[t]
            try:
                data[i, :] = [expr(*Yi.values[:9]) for expr in var_expressions_lambdified]
            except TypeError:
                # catching double entries from piecewise runs
                # resulting in end of one piece and start of
                # next piece having the same time step
                # try:
                Yi = Yi.iloc[0]
                data[i, :] = [expr(*Yi[:9]) for expr in var_expressions_lambdified]
                # except TypeError:
                #     print('Type Error at t={} in getting unified trajectory ')
                #     print(Yi)
                #     print('returning functional part of trajectory', flush=True)

        df_out = pd.DataFrame(index=t_values, columns=columns, data=data)

        return df_out
