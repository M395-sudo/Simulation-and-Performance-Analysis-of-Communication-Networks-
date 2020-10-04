'''
File name: an_mm1.py
Author: Nguyen Tuan Khai
Date created: 14/04/2020
'''

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from aux_.pyaux import *

import numpy as np, pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as tckr
import matplotlib.cm as cm
from matplotlib.widgets import CheckButtons, RadioButtons

__all__ = []
rng = np.random.default_rng()
cmaps = [cm.viridis, cm.plasma, cm.inferno, cm.magma]

def main(argv):
    simtrace_dir = os.path.join(os.path.dirname(__file__), 'simtrace')
    event_df = pd.read_csv(os.path.join(simtrace_dir, 'events.csv'))
    pkt_df = pd.read_csv(os.path.join(simtrace_dir, 'packets.csv'))

    ana = Analyser(event_df, pkt_df)
    ana.start()

class Analyser:
    def __init__(self, event_df, pkt_df):
        self.event_df = event_df
        self.pkt_df = pkt_df
        self.options = (('Inter-arrival time histogram', self.iat_hist),
                        ('Arrival number histogram', self.arvl_hist),
                        ('Service duration histogram', self.sd_hist),
                        ('Packet size histogram', self.pkt_size_hist),
                        ('Waiting time histogram', self.t_wait_hist),
                        ('Sojourn time histogram', self.t_sojrn_hist),
                        ('System state histogram', self.sys_state_hist),
                        ('Queue length histogram', self.q_len_hist),
                        ('Arrival packet rate plot', self.arvl_pkt_rate_plot),
                        ('Arrival bit rate plot', self.arvl_bit_rate_plot),
                        ('System state plot', self.sys_state_plot),
                        ('Queue length plot', self.q_len_plot),
                        ('Server state plot', self.srv_state_plot)
                      )
    # End of class constructor

    def start(self):
        while (opt:=queryPrompt(self.options)) is not None:
            # Execute the corresponding function
            opt[1]()
            input("\nPress <Enter> to continue...\n")
    # End of method `start`
    

    def sys_state_plot(self):
        sys_states = self.event_df['system state']
        tt = self.event_df['timestamp (s)']

        ctrl_ts_plot(tt, sys_states, 'Time (s)', 'System state', 'step')
    # End of method `sys_state_plot`

    def sys_state_hist(self):
        sys_states = self.event_df['system state']
        tt = self.event_df['timestamp (s)']
        
        ctrl_hist_dur(data=np.append(0, sys_states[:-1]),
                      xlabel='System state',
                      durations=np.diff(tt, prepend=0.),
                      dur_name='Duration (s)',
                      bins=np.arange(sys_states.max() + 2))
    # End of method `sys_state_hist`

    def q_len_plot(self):
        sys_states = self.event_df['system state']
        q_lens = np.clip(sys_states - 1, 0, None)
        tt = self.event_df['timestamp (s)']

        ctrl_ts_plot(tt, q_lens, 'Time (s)', 'Queue length', 'step')
    # End of method `q_len_plot`

    def q_len_hist(self):
        sys_states = self.event_df['system state']
        q_lens = np.clip(sys_states - 1, 0, None)
        tt = self.event_df['timestamp (s)']
        
        ctrl_hist_dur(data=np.append(0, q_lens[:-1]),
                      xlabel='Queue length',
                      durations=np.diff(tt, prepend=0.),
                      dur_name='Duration (s)',
                      bins=np.arange(q_lens.max() + 2))
    # End of method `q_len_hist`

    def t_wait_hist(self):
        if not (t_res:=t_res_query()):
            return
        waits = self.pkt_df['wait (ms)'].replace(np.inf, np.nan).dropna()
        bins = np.arange(waits.min(), waits.max() + t_res, t_res)

        ctrl_hist(waits, 'Waiting time (ms)', bins)
    # End of method `t_wait_hist`

    def t_sojrn_hist(self):
        if not (t_res:=t_res_query()):
            return
        df_nafree = self.pkt_df.replace(np.inf, np.nan).dropna()
        sojrns = (df_nafree['depart (s)'] - df_nafree['arrive (s)'])*1000.

        bins = np.arange(sojrns.min(), sojrns.max() + t_res, t_res)

        ctrl_hist(sojrns, 'Sojourn time (ms)', bins)
    # End of method `t_sojrn_hist`

    def arvl_pkt_rate_plot(self):
        if not (t_res:=t_res_query()):
            return
        t_res *= 1E-3 # secs

        tt = self.pkt_df['arrive (s)']
        bins = np.arange(0, tt.iloc[-1], t_res)
        pkt_rates = np.histogram(tt, bins)[0]/t_res

        ctrl_ts_plot(bins[1:] - 0.5*t_res, pkt_rates, 'Time (s)', 'Packet rate (pps)')
    # End of method `arvl_pkt_rate_plot`

    def arvl_bit_rate_plot(self):
        if not (t_res:=t_res_query()):
            return
        t_res *= 1E-3 # secs

        tt, pkt_sizes = self.pkt_df['arrive (s)'], self.pkt_df['size (bytes)']*8.
        bins = np.arange(0, tt.iloc[-1], t_res)
        thruput = np.histogram(tt, bins, weights=pkt_sizes)[0]/t_res

        ctrl_ts_plot(bins[1:] - 0.5*t_res, thruput, 'Time (s)', 'Throughput (bps)')
    # End of method `arvl_bit_rate_plot`

    def srv_state_plot(self):
        sys_states = self.event_df['system state']
        tt = self.event_df['timestamp (s)']
        srv_busy = (sys_states>0)

        ctrl_ts_plot(tt, srv_busy, 'Time (s)', 'Server state', 'step', yticks=([0,1], ['idle', 'busy']))
    # End of method `srv_state_plot`

    def iat_hist(self):
        if not (t_res:=t_res_query()):
            return

        iats = np.diff(self.pkt_df['arrive (s)'], prepend=0.)*1000.
        bins = np.arange(0, iats.max() + t_res, t_res)

        ctrl_hist(iats, 'Inter-arrival time (ms)', bins)
    # End of method `iat_hist`

    def arvl_hist(self):
        if not (t_res:=t_res_query()):
            return
        t_res *= 1E-3 # secs

        tt = self.pkt_df['arrive (s)']
        bins = np.arange(0, tt.iloc[-1], t_res)
        arvls = np.histogram(tt, bins)[0]
        hbins = np.arange(arvls.min(), arvls.max()+2)

        ctrl_hist(arvls, 'Arrivals', hbins, align='left', rwidth=0.5)
    # End of method `arvl_hist`

    def pkt_size_hist(self):
        if not (byt_res:=byt_res_query()):
            return

        pkt_sizes = self.pkt_df['size (bytes)']
        bins = np.arange(0, pkt_sizes.max() + 2, byt_res)
        
        ctrl_hist(pkt_sizes, 'Packet size (Bytes)', bins)
    # End of method `pkt_size_hist`

    def sd_hist(self):
        if not (t_res:=t_res_query()):
            return

        sds = (self.pkt_df['depart (s)'] - self.pkt_df['arrive (s)'])*1000. - self.pkt_df['wait (ms)']

        sds = sds[np.isfinite(sds)]

        bins = np.arange(0, sds.max() + t_res, t_res)

        ctrl_hist(sds, 'Service duration (ms)', bins)
    # End of method `sd_hist`

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

def byt_res_query():
    print()
    while True:
        sel = input(f"Please enter packet size resolution in Bytes? >    ").strip()

        if sel in ESC_OPTS:
            return None

        try:
            t_res = float(sel)
            return t_res
        except (IndexError, ValueError): pass
# End of function `byt_res_query`

def ctrl_ts_plot(x, y, xlabel, ylabel, typ=None, xticks=None, yticks=None):

    cmap = rng.choice(cmaps)

    fig, ax = plt.subplots()

    if typ == 'step': ax.step(x, y, 'b', where='post', color=cmap(rng.random()))
    else: ax.plot(x, y, 'b', color=cmap(rng.random()))

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)

    if xticks:
        tcks, labs = xticks
        ax.set_xticks(tcks)
        def xtck_fmt(e, pos):
            at_ticks = (e==tcks)
            return labs[np.argmax(at_ticks)] if np.any(at_ticks) else f'{e:g}'
        ax.xaxis.set_major_formatter(tckr.FuncFormatter(xtck_fmt))

    if yticks:
        tcks, labs = yticks
        ax.set_yticks(tcks)
        def ytck_fmt(e, pos):
            at_ticks = (e==tcks)
            return labs[np.argmax(at_ticks)] if np.any(at_ticks) else f'{e:g}'
        ax.yaxis.set_major_formatter(tckr.FuncFormatter(ytck_fmt))

    ax.grid(True)

    plt.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.1)

    rax1 = plt.axes([0.35, 0.91, 0.12, 0.1])
    rax2 = plt.axes([0.55, 0.91, 0.12, 0.1])
    rax1.axis(False)
    rax2.axis(False)
    check1 = CheckButtons(rax1, ['Average'])
    check2 = CheckButtons(rax2, ['Time average'])

    avg_line_ptr, tavg_line_ptr = [None], [None]

    def updateGraph(label, line_ptr, on):
        line = line_ptr[0]
        if not on:
            if line:
                line.remove()
                if len((leg:= ax.get_legend()).get_lines()) <= 1:
                    leg.remove()
                else: ax.legend()

        else:
            if line:
                ax.add_line(line)
                ax.legend()

            else:
                if label == 'Average':
                    line_ptr[0] = ax.plot(x, y.cumsum()/np.arange(1, len(x)+1), 'y', lw=2, label='Average')[0]
                    ax.legend()
                elif label == 'Time average':
                    line_ptr[0] = ax.plot(x, (np.append(0, y[:-1])*np.diff(x, prepend=0.)).cumsum()/x, 'r', lw=2, label='Time average')[0]
                    ax.legend()
        plt.draw()

    check1.on_clicked(lambda label: updateGraph(label, avg_line_ptr, check1.get_status()[0]))
    check2.on_clicked(lambda label: updateGraph(label, tavg_line_ptr, check2.get_status()[0]))

    plt.show()

    print()
    while True:
        sel = input(f"Would you like to save the data? (y/n)>    ").strip().lower()

        if sel == 'y':
            
            df = pd.DataFrame({xlabel: x, ylabel: y}).set_index(xlabel)

            try: os.mkdir(result_dir:= os.path.join(os.path.dirname(__file__), 'results'))
            except FileExistsError: pass

            file_path = os.path.join(result_dir, 'tmp_result.csv')
            try: df.to_csv(file_path)
            except PermissionError as err:
                print(f'Error!!! Failed to save data to {file_path}.')
                print('Make sure this file is not being opened.')
            return

        else:
            return
# End of function `ctrl_ts_plot`

def ctrl_hist(data, xlabel, bins=None, align='mid', rwidth=None):
    cmap = rng.choice(cmaps)
    plt.hist(data, bins, density=False, color=cmap(rng.random()), rwidth=rwidth, align=align)
    plt.grid(True)
    plt.xlabel(xlabel)

    if bins is not None:
        lmarg = rwidth/2 if rwidth else 0
        plt.xlim((bins[0] - lmarg, bins[-1]))

    ax = plt.gca()
    ax.set_axisbelow(True)

    plt.subplots_adjust(left=0.1, right=0.9, top=0.88, bottom=0.1)

    rax = plt.axes([0.3, 0.88, 0.55, 0.1])
    rax.axis(False)

    radBtn = MyRadioButtons(rax, ('Count', 'Probability density'), orientation='horizontal', active=0, activecolor='k')

    label_ptr = ['Count']
    def updateGraph(label):
        if label == label_ptr[0]:
            return

        label_ptr[0] = label
        ax.clear()
        ax.grid(True)
        ax.set_xlabel(xlabel)
        ax.set_axisbelow(True)
        ax.hist(data, bins, density=(label=='Probability density'), color=cmap(rng.random()), rwidth=rwidth, align=align)
        if bins is not None:
            ax.set_xlim((bins[0] - lmarg, bins[-1]))

        plt.draw()

    radBtn.on_clicked(updateGraph)

    plt.show()
# End of function `ctrl_hist`

def ctrl_hist_dur(data, xlabel, durations, dur_name='Duration', bins=None, rwidth=.5):
    cmap = rng.choice(cmaps)
    weight_pdf = durations/durations.sum()
    plt.hist(data, bins, weights=durations, color=cmap(rng.random()), rwidth=rwidth, align='left')
    plt.grid(True)
    plt.xlabel(xlabel)

    if bins is not None:
        lmarg = rwidth/2 if rwidth else 0
        plt.xlim((bins[0] - lmarg, bins[-1]))

    ax = plt.gca()
    ax.set_axisbelow(True)

    plt.subplots_adjust(left=0.1, right=0.9, top=0.88, bottom=0.1)

    rax = plt.axes([0.25, 0.88, 0.55, 0.1])
    rax.axis(False)

    radBtn = MyRadioButtons(rax, (dur_name, 'Probability'), orientation='horizontal', active=0, activecolor='k')

    label_ptr = [dur_name]
    def updateGraph(label):
        if label == label_ptr[0]:
            return

        label_ptr[0] = label
        ax.clear()
        ax.grid(True)
        ax.set_xlabel(xlabel)
        ax.set_axisbelow(True)
        if label == 'Probability':
            ax.hist(data, bins, weights=weight_pdf, color=cmap(rng.random()), rwidth=rwidth, align='left')
        else:
            ax.hist(data, bins, weights=durations, color=cmap(rng.random()), rwidth=rwidth, align='left')

        if bins is not None:
            ax.set_xlim((bins[0] - lmarg, bins[-1]))

        plt.draw()

    radBtn.on_clicked(updateGraph)

    plt.show()
# End of function `ctrl_hist_dur`

if __name__ == '__main__':
    main(sys.argv[1:])


