import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


class plot_routines(object):
    """
    this contains the routines to make different plots to compare the two
    types of model description
    """

    def __init__(self, micro_path='', macro_path='', rep_path=None,
                 micro_selector='', macro_selector='', rep_selector='',
                 table='dat', toffset=0):
        with pd.HDFStore(micro_path + 'mean.h5') as store:
            self.micro_mean = store.select(table, micro_selector)
        with pd.HDFStore(micro_path + 'std.h5') as store:
            self.micro_sem = store.select(table, micro_selector)
        with pd.HDFStore(macro_path + 'mean.h5') as store:
            self.macro_mean = store.select(table, macro_selector)
        with pd.HDFStore(macro_path + 'std.h5') as store:
            self.macro_sem = store.select(table, macro_selector)
        if rep_path is not None:
            print(macro_selector)
            with pd.HDFStore(rep_path + 'mean.h5') as store:
                self.rep_mean = store.select(table, rep_selector)
            with pd.HDFStore(rep_path + 'std.h5') as store:
                self.rep_sem = store.select(table, rep_selector)

        self.data_sets = [self.micro_mean, self.micro_sem,
                          self.macro_mean, self.macro_sem]
        if rep_path is not None:
            self.data_sets.append(self.rep_mean)
            self.data_sets.append(self.rep_sem)

        self.indices = []

        for d in self.data_sets:
            try:
                d.index = d.index.droplevel(['approximate', 'test', 'sample'])
            except:
                d.index = d.index.droplevel(['model', 'test', 'sample'])
            tvals = d.index.levels[3].values
            t0 = tvals[0] + toffset
            new_times = {t: t-t0 for t in tvals}
            d.rename(mapper=new_times,
                     axis='index',
                     level='tstep',
                     inplace=True)


        self.variable_combos = [['x', 'y', 'z'], ['c', 'g'], ['mu_c^c', 'mu_d^d'],
                                ['mu_c^d', 'mu_d^c']]
        self.latex_labels = [['$x$', '$y$', '$z$'], ['$c$', '$g$'],
                             ['$\mu^{(c)}_c$', '$\mu^{(d)}_d$'],
                             ['$\mu^{(c)}_d$', '$\mu^{(d)}_c$']]

        self.colors = ['#E37222', '#8E908F', '#009FDA', '#69923A']

    def mk_plots(self, bd):

        # select data for given value of bd
        local_datasets = []
        for d in self.data_sets:
            local_datasets.append(d.xs(bd, level=0))

        phi_vals = local_datasets[0].index.levels[0].values

        l_phi = len(phi_vals)
        l_vars = len(self.variable_combos)

        fig = plt.figure()
        axes = [fig.add_subplot(l_vars, l_phi, i + 1 + j * l_phi)
                for i in range(l_phi)
                for j in range(l_vars)]

        for i, phi in enumerate(phi_vals):
            for j, variables in enumerate(self.variable_combos):
                ax_id = self.grid_index(i, j, l_phi, l_vars) - 1
                # local data set for specifiv value of phi
                ldp = []
                for d in local_datasets:
                    ldp.append(d.xs(phi, level=0))
                print(self.grid_index(i, j, l_phi, l_vars))
                ldp[0][variables] \
                    .plot(
                    ax=axes[ax_id],
                    legend=False,
                    color=self.colors)
                for k, variable in enumerate(variables):
                    upper_limit = np.transpose(ldp[0][[variable]].values \
                                               + ldp[1][[variable]].values)[0]
                    lower_limit = np.transpose(ldp[0][[variable]].values \
                                               - ldp[1][[variable]].values)[0]
                    axes[ax_id].fill_between(ldp[0].index.values,
                                             upper_limit, lower_limit,
                                             color=self.colors[k],
                                             alpha=0.2)
                    ldp[2][variables] \
                        .plot(
                        ax=axes[ax_id],
                        legend=False,
                        color=self.colors,
                        style='-.')

        return fig

    def mk_opinon_plots(self, selector: dict,
                        y_limits: list,
                        legend_location: int,
                        ax: plt.axis,
                        legend: bool = True,
                        x_limits: list = [0, 900],
                        x_label: str = 't',
                        y_ticks: bool = True):

        micro_alpha = 0.8

        local_datasets = []
        for d in self.data_sets:
            local_datasets.append(d.xs(list(selector.values()), level=list(selector.keys())))

        variables = self.variable_combos[0]
        local_datasets[0][variables].plot(ax=ax,
                                          color=self.colors,
                                          alpha=micro_alpha,
                                          legend=legend)
        for k, variable in enumerate(variables):
            upper_limit = np.transpose(local_datasets[0][[variable]].values \
                                       + local_datasets[1][[variable]].values)[0]
            lower_limit = np.transpose(local_datasets[0][[variable]].values \
                                       - local_datasets[1][[variable]].values)[0]
            ax.fill_between(local_datasets[0].index.values,
                            upper_limit, lower_limit,
                            color='k',
                            alpha=0.05)
            ax.plot(local_datasets[0].index.values,
                    upper_limit,
                    color=self.colors[k],
                    alpha=0.2)
            ax.plot(local_datasets[0].index.values,
                    lower_limit,
                    color=self.colors[k],
                    alpha=0.2)

            local_datasets[2][[variable]] \
                .plot(ax=ax,
                      color=self.colors[k],
                      legend=False,
                      style='--',
                      linewidth=2
                      )
        ax.set_ylim(y_limits)
        ax.set_xlim(x_limits)
        ax.set_xlabel(x_label)
        k = len(variables)
        patches, labels = ax.get_legend_handles_labels()
        labels = self.latex_labels[0]
        if not y_ticks:
            ax.set_yticklabels([])
            ax.set_ylabel('')
        if legend:
            lg = ax.legend(patches[:k], labels[:k],
                           loc=legend_location,
                           title='',
                           fontsize=12)
            lg.get_frame().set_alpha(0.8)

    def mk_4plots(self, selector: dict,
                  upper_limits: list = [1., 80, 11, 10],
                  lower_limits: list = [-.8, 0., 0., 0.],
                  legend_locations: list = [4, 7, 1, 7],
                  tmax: int = 1000, tmin: int = 0,
                  plot_rep=False,
                  figsize=(8, 6)):

        self.variable_combos = [['x', 'y', 'z'], ['c', 'g'], ['mu_c^c', 'mu_d^d'],
                                ['mu_c^d', 'mu_d^c']]
        self.latex_labels = [['$x$', '$y$', '$z$'], ['$c$', '$g$'],
                             ['$\mu^{(c)}_c$', '$\mu^{(d)}_d$'],
                             ['$\mu^{(c)}_d$', '$\mu^{(d)}_c$']]

        # set opacity for plots of micro data:
        micro_alpha = 0.8
        macro_alpha = 1.
        if plot_rep:
            micro_alpha = 0.5
            macro_alpha = .6
        # select data for given value of bd and phi
        local_datasets = []
        for d in self.data_sets:
            local_datasets.append(d.xs(list(selector.values()), level=list(selector.keys())))

        l_vars = len(self.variable_combos)
        fig = plt.figure(figsize=figsize)
        axes = [fig.add_subplot(2, 2, i + 1) for i in range(l_vars)]

        for j, variables in enumerate(self.variable_combos):
            ax_id = j
            axes[ax_id].set_xlim([tmin, tmax])
            # local data set for specify value of phi
            ldp = local_datasets
            if j == 1:
                # clone axis for plot of knowledge stock
                c_ax = axes[ax_id].twinx()
                c_ax.set_xlim([tmin, tmax])
                ldp[0][variables[0]] \
                    .plot(
                    ax=axes[ax_id],
                    color=self.colors[0],
                    alpha=micro_alpha)
                ldp[0][variables[1]] \
                    .plot(
                    ax=c_ax,
                    color=self.colors[1],
                    alpha=micro_alpha)
            else:
                ldp[0][variables] \
                    .plot(
                    ax=axes[ax_id],
                    color=self.colors,
                    alpha=micro_alpha)
            for k, variable in enumerate(variables):
                ax = axes[ax_id]
                if variable == 'g':
                    ax = c_ax
                    c_ax.set_ylim([lower_limits[-1], upper_limits[-1]])

                upper_limit = np.transpose(ldp[0][[variable]].values \
                                           + ldp[1][[variable]].values)[0]
                lower_limit = np.transpose(ldp[0][[variable]].values \
                                           - ldp[1][[variable]].values)[0]
                ax.fill_between(ldp[0].index.values,
                                upper_limit, lower_limit,
                                color='k',
                                alpha=0.05)
                ax.plot(ldp[0].index.values,
                        upper_limit,
                        color=self.colors[k],
                        alpha=0.2)
                ax.plot(ldp[0].index.values,
                        lower_limit,
                        color=self.colors[k],
                        alpha=0.2)

                # Plot macro data.
                ldp[2][[variable]] \
                    .plot(ax=ax,
                          color=self.colors[k],
                          legend=False,
                          style='--',
                          linewidth=2,
                          alpha=macro_alpha)


            ax = axes[ax_id]
            ax.set_ylim([lower_limits[j], upper_limits[j]])
            k = len(variables)
            patches, labels = ax.get_legend_handles_labels()
            labels = self.latex_labels[j]
            if j == 1:
                gArtist = plt.Line2D((0, 1), (0, 0), color=self.colors[1])
                cArtist = plt.Line2D((0, 1), (0, 0), color=self.colors[0])
                patches = [cArtist, gArtist]
            if j is 0:
                ax.set_xticklabels([])
                ax.set_xlabel('')
            else:
                ax.set_xlabel('t')
            lg = ax.legend(patches[:k], labels[:k],
                           loc=legend_locations[ax_id],
                           title='',
                           fontsize=12)
            lg.get_frame().set_alpha(0.8)

            # ax.set_title('')
            # ax.set_loc

        return fig, axes

    def mk_4plots_v2(self, selector: dict,
                  upper_limits: list = [1., 80, 11, 10],
                  lower_limits: list = [-.8, 0., 0., 0.],
                  legend_locations: list = [4, 7, 1, 7],
                  tmax: int = 1000, tmin: int = 0,
                  plot_rep=False,
                  figsize=(8, 6)):

        self.variable_combos = [['N_c over N', '[cc] over M', '[cd] over M'],
                                ['C', 'G'], ['K_c^c', 'K_d^d'],
                                ['K_c^d', 'K_d^c']]
        self.variable_combos_backup = [['N_c over N', '[cc] over M', '[cd] over M'],
                                ['c', 'g'], ['K_c^c', 'K_d^d'],
                                ['K_c^d', 'K_d^c']]
        self.latex_labels = [['$N_c / N$', '$[cc] / M$', '$[cd] / M$'],
                             ['$C$', '$G$'],
                             ['$K^{(c)}_c$', '$K^{(d)}_d$'],
                             ['$K^{(c)}_d$', '$K^{(d)}_c$']]

        # set opacity for plots of micro data:
        micro_alpha = 0.8
        macro_alpha = 1.
        if plot_rep:
            micro_alpha = 0.5
            macro_alpha = .6
        # select data for given value of bd and phi
        local_datasets = []
        for d in self.data_sets:
            local_datasets.append(d.xs(list(selector.values()), level=list(selector.keys())))

        l_vars = len(self.variable_combos)
        fig = plt.figure(figsize=figsize)
        axes = [fig.add_subplot(2, 2, i + 1) for i in range(l_vars)]

        for j, variables in enumerate(self.variable_combos):
            ax_id = j
            axes[ax_id].set_xlim([tmin, tmax])
            # local data set for specify value of phi
            ldp = local_datasets
            print(j, variables)
            if j == 1:
                # clone axis for plot of knowledge stock
                c_ax = axes[ax_id].twinx()
                axes.append(c_ax)
                c_ax.set_xlim([tmin, tmax])
                ldp[0][variables[0]] \
                    .plot(
                    ax=axes[ax_id],
                    color=self.colors[0],
                    alpha=micro_alpha)
                ldp[0][variables[1]] \
                    .plot(
                    ax=c_ax,
                    color=self.colors[1],
                    alpha=micro_alpha)
            else:
                ldp[0][variables] \
                    .plot(
                    ax=axes[ax_id],
                    color=self.colors,
                    alpha=micro_alpha)
            for k, variable in enumerate(variables):
                ax = axes[ax_id]
                if variable == 'g' or variable == 'G':
                    ax = c_ax
                    c_ax.set_ylim([lower_limits[-1], upper_limits[-1]])

                upper_limit = np.transpose(ldp[0][[variable]].values \
                                           + ldp[1][[variable]].values)[0]
                lower_limit = np.transpose(ldp[0][[variable]].values \
                                           - ldp[1][[variable]].values)[0]
                ax.fill_between(ldp[0].index.values,
                                upper_limit, lower_limit,
                                color='k',
                                alpha=0.05)
                ax.plot(ldp[0].index.values,
                        upper_limit,
                        color=self.colors[k],
                        alpha=0.2)
                ax.plot(ldp[0].index.values,
                        lower_limit,
                        color=self.colors[k],
                        alpha=0.2)

                # Plot macro data.
                try:
                    ldp[2][[variable]] \
                        .plot(ax=ax,
                              color=self.colors[k],
                              legend=False,
                              style='--',
                              linewidth=2,
                              alpha=macro_alpha)
                except KeyError:
                    print(f'Key Error for {self.variable_combos[j]} in dataset {k}')
                    (100 * ldp[2][self.variable_combos_backup[j][k]]) \
                        .plot(ax=ax,
                              color=self.colors[k],
                              legend=False,
                              style='--',
                              linewidth=2,
                              alpha=macro_alpha)

            ax = axes[ax_id]
            ax.set_ylim([lower_limits[j], upper_limits[j]])
            k = len(variables)
            patches, labels = ax.get_legend_handles_labels()
            labels = self.latex_labels[j]
            if j == 1:
                gArtist = plt.Line2D((0, 1), (0, 0), color=self.colors[1])
                cArtist = plt.Line2D((0, 1), (0, 0), color=self.colors[0])
                patches = [cArtist, gArtist]
            if j is 0:
                ax.set_xticklabels([])
                ax.set_xlabel('')
            else:
                ax.set_xlabel('t')
            lg = ax.legend(patches[:k], labels[:k],
                           loc=legend_locations[ax_id],
                           title='',
                           fontsize=12)
            lg.get_frame().set_alpha(0.8)

            # ax.set_title('')
            # ax.set_loc

        return fig, axes

    def mk_4plots_rp_overlay(self, selector: dict,
                  upper_limits: list = [1., 80, 11, 10],
                  lower_limits: list = [-.8, 0., 0., 0.],
                  legend_locations: list = [4, 7, 1, 7],
                  tmax: int = 1000, tmin: int = 0,
                  figsize=(8, 6)):

        self.variable_combos = [['n_c', 'i_c'], ['c', 'g'], ['k_c', 'k_d'],
                                ['r_c', 'r_d']]
        self.latex_labels = [['$n_c$', '$i_c$'], ['$c$', '$g$'],
                             ['$k_c$', '$k_d$'],
                             ['$r_c$', '$r_d$']]

        # set opacity for plots of micro data:
        micro_alpha = 0.5
        macro_alpha = .6
        # select data for given value of bd and phi
        local_datasets = []
        for d in self.data_sets:
            local_datasets.append(d.xs(list(selector.values()), level=list(selector.keys())))

        l_vars = len(self.variable_combos)
        fig = plt.figure(figsize=figsize)
        axes = [fig.add_subplot(2, 2, i + 1) for i in range(l_vars)]

        for j, variables in enumerate(self.variable_combos):
            ax_id = j
            axes[ax_id].set_xlim([tmin, tmax])
            # local data set for specify value of phi
            ldp = local_datasets
            if j == 1:
                # clone axis for plot of knowledge stock
                c_ax = axes[ax_id].twinx()
                c_ax.set_ylabel('c')
                c_ax.set_xlim([tmin, tmax])
                axes[ax_id].set_ylabel('g')
                ldp[0][variables[0]] \
                    .plot(
                    ax=axes[ax_id],
                    color=self.colors[0],
                    alpha=micro_alpha)
                ldp[0][variables[1]] \
                    .plot(
                    ax=c_ax,
                    color=self.colors[1],
                    alpha=micro_alpha)
            #
            # elif j == 3:
            #     # clone axis for plot of wages
            #     w_ax = axes[ax_id].twinx()
            #     w_ax.set_ylabel('r')
            #     axes[ax_id].set_ylabel('w')
            #     ldp[0][variables[:2]] \
            #         .plot(
            #         ax=axes[ax_id],
            #         color=self.colors[0],
            #         alpha=micro_alpha)
            #     ldp[0][variables[2]] \
            #         .plot(
            #         ax=w_ax,
            #         color=self.colors[1],
            #         alpha=micro_alpha)

            else:
                ldp[0][variables] \
                    .plot(
                    ax=axes[ax_id],
                    color=self.colors,
                    alpha=micro_alpha)


            for k, variable in enumerate(variables):
                ax = axes[ax_id]
                if variable == 'g':
                    ax = c_ax
                    c_ax.set_ylim([lower_limits[-2], upper_limits[-2]])
                # if variable == 'w':
                #     ax = w_ax
                #     w_ax.set_ylim([lower_limits[-1], upper_limits[-1]])

                upper_limit = np.transpose(ldp[0][[variable]].values \
                                           + ldp[1][[variable]].values)[0]
                lower_limit = np.transpose(ldp[0][[variable]].values \
                                           - ldp[1][[variable]].values)[0]
                ax.fill_between(ldp[0].index.values,
                                upper_limit, lower_limit,
                                color='k',
                                alpha=0.05)
                ax.plot(ldp[0].index.values,
                        upper_limit,
                        color=self.colors[k],
                        alpha=0.2)
                ax.plot(ldp[0].index.values,
                        lower_limit,
                        color=self.colors[k],
                        alpha=0.2)

                # Plot macro data.
                ldp[2][[variable]] \
                    .plot(ax=ax,
                          color=self.colors[k],
                          legend=False,
                          style='--',
                          linewidth=2,
                          alpha=macro_alpha)
                # Plot approximate data in the same way.
                ldp[4][[variable]] \
                    .plot(ax=ax,
                          color=self.colors[k],
                          legend=False,
                          style='-.',
                          linewidth=2)
            ax = axes[ax_id]
            ax.set_ylim([lower_limits[j], upper_limits[j]])
            k = len(variables)
            patches, labels = ax.get_legend_handles_labels()
            labels = self.latex_labels[j]
            if j == 1:
                gArtist = plt.Line2D((0, 1), (0, 0), color=self.colors[1])
                cArtist = plt.Line2D((0, 1), (0, 0), color=self.colors[0])
                patches = [cArtist, gArtist]
            if j is 0:
                ax.set_xticklabels([])
                ax.set_xlabel('')
            else:
                ax.set_xlabel('t')
            lg = ax.legend(patches[:k], labels[:k],
                           loc=legend_locations[ax_id],
                           title='',
                           fontsize=12)
            lg.get_frame().set_alpha(0.8)

            # ax.set_title('')
            # ax.set_loc

        return fig, axes

    def grid_index(self, row, col, n_rows, n_cols):
        """
        calculate index number in subplot grids
        grid_index(0,0) = 1 ~ upper left corner
        to index the axis list, one might use grid_index - 1
        """
        return col + 1 + row * n_cols

    def plot_L2_distance(self, selector: dict):
        pass