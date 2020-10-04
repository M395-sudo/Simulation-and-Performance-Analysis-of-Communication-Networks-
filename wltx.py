'''
File name: wltx.py
Author: Nguyen Tuan Khai
Date created: 14/04/2020
'''

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from collections.abc import Iterable
from aux_.pyaux import *
from student.implement import *
import numpy as np
import pandas as pd
__all__ = []
rng = np.random.default_rng()

def main():
        # Feel free to modify the parameter "sim_time_limit".
    sim_time_limit           = 60        # seconds
    mean_inter_arrival_time  =     # seconds
    mean_pkt_size            =     # Bytes
    bit_error_probability    = 

    simulator = WlTx_Sim(t_limit=sim_time_limit,
                        mean_iat=mean_inter_arrival_time,
                        mean_pkt_size=mean_pkt_size,
                        beps=bit_error_probability)

    simulator.simulate()
# End of function `main`

class WlTx_Sim:

    def simulate(self):
        print('Simulation has started.')
        self.generate_packets()
        self.compute_faulty()
        self.save_simulation_results()
        input('\nPress <Enter> to finish.\n')
    # End of method `simulate`

    def __init__(self, t_limit, mean_iat, mean_pkt_size, beps):
        self.t_limit = t_limit
        self.mean_iat = mean_iat
        self.mean_pkt_size = mean_pkt_size
        if isinstance(beps, Iterable): self.beps = beps
        else: self.beps = [beps]
        self.run_num = len(self.beps)
    # End of class constructor

    def generate_packets(self):
        # Pre-estimate number of arrivals
        lamb = self.t_limit*self.run_num/self.mean_iat
            # 3.29 below is just a heuristic number
        arvl_num = np.ceil(lamb + 3.29*lamb**.5).astype(np.int0)

        iats = generate_rand_iats_in_sec(self.mean_iat, arvl_num)
        while iats.sum() < self.t_limit:
            iats = np.concatenate((iats, generate_rand_iats_in_sec(self.mean_iat, arvl_num)))

        arvl_times = iats.cumsum()

        self.iats = iats[(msk:= arvl_times<=self.t_limit*self.run_num)]
        self.arvl_times = arvl_times[msk]

        # How many packets are generated?
        pkt_num = len(self.arvl_times)

        # What are the packet sizes?
        pkt_sizes = np.ceil(generate_rand_pkt_sizes_in_byte(self.mean_pkt_size, pkt_num))

        # Make sure all sizes are non-zero
        while np.any(zero_msk:=pkt_sizes==0):
            pkt_sizes[zero_msk] = np.ceil(generate_rand_pkt_sizes_in_byte(self.mean_pkt_size, zero_msk.sum()))

        # Assign values to class attributes
        self.pkt_num = pkt_num
        self.pkt_sizes = pkt_sizes
    # End of method `generate_arrival_times`

    def compute_faulty(self):
        bins = np.arange(0, self.arvl_times[-1] + self.t_limit, self.t_limit)
        run_ids = np.digitize(self.arvl_times, bins, right=True) - 1

        faultys1, faultys2 = np.zeros((2, self.pkt_num), bool)
        t_last = 0.
        for run, bep in enumerate(self.beps):
            filt = (run_ids==run)
            pkt_num = filt.sum()
            pkt_sizes_in_byte = self.pkt_sizes[filt]
            
            # Which packets are faulty and which are not?
            if bep > 0:
                faulty1 = (rng.geometric(bep, pkt_num) <= pkt_sizes_in_byte*8)
                faulty2 = generate_faulty_packets(bep, pkt_num, pkt_sizes_in_byte.astype(np.int0))

                faultys1[filt], faultys2[filt] = faulty1, faulty2

            self.arvl_times[filt] -= t_last
            t_last += self.arvl_times[filt][-1]

        self.faultys1 = faultys1
        self.faultys2 = faultys2
        self.ag_beps = np.asarray(self.beps)[run_ids]
    # End of method `compute_system_events`

    def save_simulation_results(self):
        print('\nSaving simulation trace... ', end='', flush=True)

        trace_dir = os.path.join(os.path.dirname(__file__), 'simtrace')

        try: os.mkdir(trace_dir)
        except FileExistsError: pass

        # Store packet list
        pkt_df = pd.DataFrame({ 'packet id': np.arange(self.pkt_num),
                                'bep': self.ag_beps,
                                'size (bytes)': self.pkt_sizes,
                                'arrive (s)': self.arvl_times,
                                'faulty fast': self.faultys1,
                                'faulty strforw': self.faultys2}).set_index('packet id')

        file_path = os.path.join(trace_dir, 'packets.csv')

        try: pkt_df.to_csv(file_path)
        except PermissionError as err:
            print(f'\033[1m\033[31m\nError!!! Failed to store simulation trace to "{file_path}".')
            print('Make sure this file is not being opened.\033[0m')
            return
        print('Done!')
    # End of method `save_simulation_results`

if __name__ == '__main__':
    clscr()
    main()