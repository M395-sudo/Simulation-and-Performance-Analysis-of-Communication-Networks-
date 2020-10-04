'''
File name: an_wltx.py
Author: Nguyen Tuan Khai
Date created: 14/04/2020
'''

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from aux_.pyaux import *

import numpy as np, pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm as cm

from student.implement import *

__all__ = []

rng = np.random.default_rng()
cmaps = [cm.viridis, cm.plasma, cm.inferno, cm.magma]

def main(argv):
    simtrace_dir = os.path.join(os.path.dirname(__file__), 'simtrace')
    pkt_df = pd.read_csv(os.path.join(simtrace_dir, 'packets.csv'))

    ana = Analyser(pkt_df)
    ana.start()

class Analyser:
    def __init__(self, pkt_df):
        self.pkt_df = pkt_df
        self.options = (('Packet rate plot', self.pkt_rate_plot),
                        ('Throughput plot', self.thruput_plot),
                        ('Good packet rate plot', self.good_pkt_rate_plot),
                        ('Goodput plot', self.goodput_plot),
                        ('Good packet rate comparison', self.pkt_rate_compare),
                        ('Goodput comparison', self.goodput_compare),
                        ('Packet survival probability', self.survl_probability),
                        ('Goodput confidence intervals', self.goodput_interval),
                      )
    # End of class constructor

    def start(self):
        while (opt:=queryPrompt(self.options)) is not None:
            # Execute the corresponding function
            opt[1]()
            input("\nPress <Enter> to continue...\n")
    # End of method `start`
    

    def survl_probability(self):
        # Group by bit error probability
        surl_probs = self.pkt_df.groupby('bep')['faulty fast'].apply(lambda e: (~e).sum()/len(e))
        cat_bar(surl_probs.index, surl_probs, 'Bit error probability', 'Packet survival probability')
    # End of method `survl_probability`

    
    def get_good_pkt_rate(self):
        if not (t_res:=t_res_query()):
            return
        t_res *= 1E-3 # secs

        def anonymous(df):
            tt = df['arrive (s)']
            bins = np.arange(0, df['arrive (s)'].iloc[-1], t_res)
            
            survl_grp1 = df.groupby('faulty fast').get_group(False)
            survl_grp2 = df.groupby('faulty strforw').get_group(False)
            
            survls1, _ = np.histogram(survl_grp1['arrive (s)'], bins)
            survls2, _ = np.histogram(survl_grp2['arrive (s)'], bins)

            good_pkt_rates1 = survls1/t_res
            good_pkt_rates2 = survls2/t_res

            x = bins[1:] - 0.5*t_res

            return pd.DataFrame({'Fast': good_pkt_rates1, 'Straightforward': good_pkt_rates2, 'x': x})

        self.good_pkt_rates = self.pkt_df.groupby('bep').apply(anonymous).groupby('bep')
        self.t_res = t_res
        return True
    # End of method `get_good_pkt_rate`

    def get_goodput(self):
        if not (t_res:=t_res_query()):
            return
        t_res *= 1E-3 # secs

        def anonymous(df):
            tt = df['arrive (s)']
            bins = np.arange(0, df['arrive (s)'].iloc[-1], t_res)
            
            survl_grp1 = df.groupby('faulty fast').get_group(False)
            survl_grp2 = df.groupby('faulty strforw').get_group(False)
            
            survlbytes1, _ = np.histogram(survl_grp1['arrive (s)'], bins, weights=survl_grp1['size (bytes)'])
            survlbytes2, _ = np.histogram(survl_grp2['arrive (s)'], bins, weights=survl_grp2['size (bytes)'])

            goodputs1 = survlbytes1*(8./t_res)
            goodputs2 = survlbytes2*(8./t_res)

            x = bins[1:] - 0.5*t_res

            return pd.DataFrame({'Fast': goodputs1, 'Straightforward': goodputs2, 'x':x})

        self.goodputs = self.pkt_df.groupby('bep').apply(anonymous).groupby('bep')
        self.t_res = t_res
        return True
    # End of method `get_goodput`

    def goodput_interval(self):
        if not self.get_goodput(): return
        if not (sampl_sz:=sampl_size_query()): return

        sampls = self.goodputs.apply(lambda df: np.split(df['Fast'], np.arange(sampl_sz, len(df), sampl_sz))[:-1])
        sampls = sampls.apply(lambda sam: rng.choice(sam, min(101, len(sam)), replace=False))

        ag_means = self.goodputs['Fast'].mean()

        for bep in sampls.index:
            sampl_df = pd.DataFrame.from_dict(dict(enumerate(sampls.loc[bep])), orient='index').T

            counts = sampl_df.count()
            means = sampl_df.mean()
            stdevs = sampl_df.std()

            yerrs = get_errors(.95, counts, stdevs)

            fig, ax = plt.subplots()
            ax.errorbar(sampl_df.columns, means, yerr=yerrs, fmt='o', c=rng.choice(cmaps)(rng.random()))

            ax.hlines(ag_means.loc[bep], sampl_df.columns.min(), sampl_df.columns.max()+1, color='r', lw=2)

            ax.set_xlabel('Sample')
            ax.set_ylabel('Goodput (bps)')

            ax.set_title(f'BEP = {bep}')
            
            ax.xaxis.grid(False)
            ax.yaxis.grid(True)
            ax.set_axisbelow(True)

        plt.tight_layout()
        plt.show()
    # End of method `goodput_interval`

    def pkt_rate_compare(self):
        self.get_good_pkt_rate()
        compare_plot(self.good_pkt_rates, 'Good packet rate (pps)')
    # End of method `pkt_rate_compare`

    def goodput_compare(self):
        self.get_goodput()
        compare_plot(self.goodputs, 'Goodput (bps)')
    # End of method `goodput_compare`

    def goodput_plot(self):
        self.get_goodput()

        ctrl_ts_plot_multi(self.goodputs, 'Time (s)', 'Goodput (bps)')
    # End of method `goodput_plot`
    
    def good_pkt_rate_plot(self):
        self.get_good_pkt_rate()

        ctrl_ts_plot_multi(self.good_pkt_rates, 'Time (s)', 'Good packet rate (pps)')
    # End of method `good_pkt_rate_plot`


    def pkt_rate_plot(self):
        if not (t_res:=t_res_query()):
            return
        t_res *= 1E-3 # secs

        # Get only the first run
        pkt_df = self.pkt_df.groupby('bep').get_group(self.pkt_df.loc[0, 'bep'])

        tt = pkt_df['arrive (s)']
        bins = np.arange(0, tt.iloc[-1] + t_res, t_res)
        arvls, _ = np.histogram(tt, bins)
        pkt_rates = arvls/t_res

        ctrl_ts_plot(bins[1:] - 0.5*t_res, pkt_rates, 'Time (s)', 'Packet rate (pps)')
    # End of method `arvl_pkt_rate_plot`

    def thruput_plot(self):
        if not (t_res:=t_res_query()):
            return
        t_res *= 1E-3 # secs

        # Get only the first run
        pkt_df = self.pkt_df.groupby('bep').get_group(self.pkt_df.loc[0, 'bep'])

        tt = pkt_df['arrive (s)']
        
        bins = np.arange(0, tt.iloc[-1] + t_res, t_res)
        arvlbytes, _ = np.histogram(tt, bins, weights=pkt_df['size (bytes)'])
        thruputs = arvlbytes*(8./t_res)

        ctrl_ts_plot(bins[1:] - 0.5*t_res, thruputs, 'Time (s)', 'Throughput (bps)')
    # End of method `arvl_bit_rate_plot`


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

def sampl_size_query():
    print()
    while True:
        sel = input(f"Please enter the sample size? >    ").strip()

        if sel in ESC_OPTS:
            return None

        try:
            sampl_sz = int(sel)
            return sampl_sz
        except (IndexError, ValueError): pass
# End of function `chunk_query`


def ctrl_ts_plot(x, y, xlabel, ylabel):
    fig, ax = plt.subplots()

    ax.plot(x, y, c=rng.choice(cmaps)(.5))

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)

    ax.grid(True)
    
    plt.show()
# End of function `ctrl_ts_plot`

def ctrl_ts_plot_multi(grb, xlabel, ylabel):

    for bep in grb.indices:
        grp = grb.get_group(bep)

        lab1, lab2, labx = grp.keys()
        y1, y2, x = grp[lab1], grp[lab2], grp[labx]

        fig, ax = plt.subplots()
        cmap = rng.choice(cmaps)

        ax.plot(x, y1, color=cmap(.25), label=lab1)
        ax.plot(x, y2, color=cmap(.75), label=lab2)

        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)

        ax.legend()
        ax.grid(True)

        ax.set_title(f'BEP = {bep}')

    plt.tight_layout()
    plt.show()
# End of function `ctrl_ts_plot_multi`

def compare_plot(grb, ylabel):

    for bep in grb.indices:
        cmap = rng.choice(cmaps)

        fig, ax = plt.subplots()

        grp = grb.get_group(bep)

        lab1, lab2, *_ = grp.keys()
        y1, y2 = grp[lab1], grp[lab2]

        x1 = rng.normal(size=(sz1:=len(y1)), scale=0.03)
        x2 = rng.normal(size=(sz2:=len(y2)), scale=0.03) + 1
        ax.scatter(x1, y1, ec=[cmap(.25)], c='none')
        ax.scatter(x2, y2, ec=[cmap(.75)], c='none')

        yerr1 = (y1.std()/sz1**.5)*get_student_t_z(.95, sz1)
        yerr2 = (y2.std()/sz2**.5)*get_student_t_z(.95, sz2)

        ax.errorbar(0, y1.mean(), yerr=yerr1, markersize=10, marker='o', capsize=15, elinewidth=2, capthick=2, c=cmap(.75))
        ax.errorbar(1, y2.mean(), yerr=yerr2, markersize=10, marker='o', capsize=15, elinewidth=2, capthick=2, c=cmap(.25))

        ax.set_ylabel(ylabel)
        ax.set_xticks((0,1)); ax.set_xticklabels((lab1, lab2))
        
        ax.xaxis.grid(False)
        ax.yaxis.grid(True)
        ax.set_axisbelow(True)

        ax.set_title(f'BEP = {bep}')

    plt.tight_layout()

    plt.show()
# End of function `compare_plot`


def cat_bar(cats, ys, xlabel, ylabel):
    fig, ax = plt.subplots()
    x = np.arange(len(cats))
    ax.bar(x, ys, color=rng.choice(cmaps)(rng.random()))

    ax.set_xticks(x)
    ax.set_xticklabels(cats)

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    
    ax.xaxis.grid(False)
    ax.yaxis.grid(True)
    ax.set_axisbelow(True)
    
    plt.show()
# End of function `cat_bar`

if __name__ == '__main__':
    main(sys.argv[1:])


