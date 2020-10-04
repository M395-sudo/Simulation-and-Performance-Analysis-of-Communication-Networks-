'''
File name: an_diffserv.py
Author: Nguyen Tuan Khai
Date created: 14/04/2020
'''

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from aux_.pyaux import *

import numpy as np, pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm as cm

__all__ = []

def main(argv):
    simtrace_dir = os.path.join(os.path.dirname(__file__), 'simtrace')
    event_df = pd.read_csv(os.path.join(simtrace_dir, 'events.csv'))
    pkt_df = pd.read_csv(os.path.join(simtrace_dir, 'packets.csv'))
    app_df = pd.read_csv(os.path.join(simtrace_dir, 'apps.csv'))

    ana = Analyser(event_df, pkt_df, app_df)
    ana.start()

class Analyser:
    def __init__(self, event_df, pkt_df, app_df):
        self.event_df = event_df
        self.event_df[['app id', 'size (bytes)']] = pkt_df.loc[event_df['incident packet'], ['app id', 'size (bytes)']].reset_index(drop=True)
        self.options = (('Packet rate plot', self.pkt_rate_plot),
                        ('Throughput plot', self.thruput_plot)
                      )
    # End of class constructor

    def start(self):
        while (opt:=queryPrompt(self.options)) is not None:
            # Execute the corresponding function
            opt[1]()
            input("\nPress <Enter> to continue...\n")
    # End of method `start`

    def pkt_rate_plot(self):
        if not (t_res:=t_res_query()):
            return
        t_res *= 1E-3 # secs

        t_last = self.event_df['timestamp (s)'].iloc[-1]
        bins = np.arange(0, t_last, t_res)
        x = bins[1:] - 0.5*t_res

        grb = self.event_df.groupby(['type', 'app id'])

        hist_df = grb['timestamp (s)'].apply(lambda e: (x, np.histogram(e, bins)[0]/t_res))

        arvl_sr, dprt_sr = hist_df['arvl'], hist_df['dprt']

        ctrl_ts_plot(arvl_sr, dprt_sr, 'Time (s)', 'Packet rate (pps)')
    # End of method `arvl_pkt_rate_plot`

    def thruput_plot(self):
        if not (t_res:=t_res_query()):
            return
        t_res *= 1E-3 # secs

        t_last = self.event_df['timestamp (s)'].iloc[-1]
        bins = np.arange(0, t_last, t_res)
        x = bins[1:] - 0.5*t_res

        grb = self.event_df.groupby(['type', 'app id'])

        hist_df = grb.apply(lambda arg_df: (x, np.histogram(arg_df['timestamp (s)'], bins, weights=arg_df['size (bytes)']*8.)[0]/t_res))

        arvl_sr, dprt_sr = hist_df['arvl'], hist_df['dprt']

        ctrl_ts_plot(arvl_sr, dprt_sr, 'Time (s)', 'Throughput (bps)')
    # End of method `arvl_bit_rate_plot`

def t_res_query():
    print()
    while True:
        sel = input(f"Please enter time resolution in milliseconds? >    ").strip()

        if sel in ESC_OPTS:
            return None

        try:
            t_res = float(sel)
            return t_res
        except (IndexError, ValueError): pass
# End of function `t_res_query`

def ctrl_ts_plot(arvl_app_dat, dprt_app_dat, xlabel, ylabel):

    apps = arvl_app_dat.keys()

    cmap = cm.inferno
    colr = np.arange(0.5/len(apps), 1, 1/len(apps))

    a_ax = plt.subplot(121)
    d_ax = plt.subplot(122)

    for c, app in zip(colr, apps):
        x, y = arvl_app_dat[app]
        a_ax.plot(x, y, color=cmap(c), label=f'App {app}')

        try:
            x, y = dprt_app_dat[app]
            d_ax.plot(x, y, color=cmap(c), label=f'App {app}')
        except KeyError: pass

    a_ax.set_xlabel(xlabel);  a_ax.set_ylabel(ylabel)
    d_ax.set_xlabel(xlabel); #d_ax.set_ylabel(ylabel)

    a_ax.legend(); d_ax.legend()

    a_ax.grid(True); d_ax.grid(True)

    a_ax.set_title('Arrival')
    d_ax.set_title('Departure')

    y_lb, y_ub = np.column_stack((a_ax.get_ylim(), d_ax.get_ylim()))
    a_ax.set_ylim(y_lb.min(), y_ub.max())
    d_ax.set_ylim(y_lb.min(), y_ub.max())

    plt.show()
# End of function `ctrl_ts_plot`

def queryPrompt(options):
    clscr()
    opt_len = len(options)
    print("\n=============== Welcome to Discrete-event Simulation Lab ==============")
    print("-- Please select what you want by entering the corresponding number. --\n")
    for i, opt in enumerate(options, 1):
        print(f'\t{i:<2}:\t{opt[0]}')
    print(f'\te :\tExit')

    print()
    while True:
        sel = input(f"What shall be selected (1-{opt_len})? >    ").strip()

        if sel in ESC_OPTS:
            print("============================ Thanks! Bye! =============================\n")
            return None

        try:
            opt = options[int(sel) - 1]
            print(f"You selected:\t{opt[0]}\n")
            return opt
        except (IndexError, ValueError): pass
# End of function `queryPrompt`

if __name__ == '__main__':
    main(sys.argv[1:])


