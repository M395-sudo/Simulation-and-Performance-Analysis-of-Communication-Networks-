'''
File name: mm1.py
Author: Nguyen Tuan Khai
Date created: 14/04/2020
'''

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from aux_.pyaux import *
from student.implement import *
import numpy as np
import pandas as pd

def main():
        # Feel free to modify the parameter "sim_time_limit".
    sim_time_limit           = 60        # seconds
    queue_capacity           = np.inf    # packets
    mean_inter_arrival_time  =     # seconds
    mean_pkt_size            =     # Bytes
    out_rate                 =     # bps

    simulator = MM1_Sim(t_limit=sim_time_limit,
                        q_cap=queue_capacity,
                        mean_iat=mean_inter_arrival_time,
                        mean_pkt_size=mean_pkt_size,
                        out_rate=out_rate)

    simulator.simulate()
# End of function `main`

class MM1_Sim:

    def simulate(self):
        print('Simulation has started.')
        self.generate_arrival_times()
        self.compute_system_events()
        self.save_simulation_results()
        input('\nPress <Enter> to finish.\n')
    # End of method `simulate`

    def __init__(self, t_limit, q_cap, mean_iat, mean_pkt_size, out_rate):
        self.t_limit = t_limit
        self.q_cap = q_cap
        self.mean_iat = mean_iat
        self.mean_pkt_size = mean_pkt_size
        self.out_rate = out_rate
    # End of class constructor

    def generate_arrival_times(self):
        # Pre-estimate number of arrivals
        lamb = self.t_limit/self.mean_iat
            # 3.29 below is just a heuristic number
        arvl_num = np.ceil(lamb + 3.29*lamb**.5).astype(np.int0)

        iats = generate_rand_iats_in_sec(self.mean_iat, arvl_num)
        while iats.sum() < self.t_limit:
            iats = np.concatenate((iats, generate_rand_iats_in_sec(self.mean_iat, arvl_num)))

        arvl_times = iats.cumsum()

        self.iats = iats[(msk:= arvl_times<=self.t_limit)]
        self.arvl_times = arvl_times[msk]
    # End of method `generate_arrival_times`

    def compute_departure_times(self):
        pkt_num = len(self.arvl_times)

        pkt_sizes = np.ceil(generate_rand_pkt_sizes_in_byte(self.mean_pkt_size, pkt_num))
        srv_durs = get_srv_durations_in_sec(pkt_sizes, self.out_rate)
        
        t_wait, t_sojrn = 0., 0.
        waits = []

        if self.q_cap == np.inf:
            # It's easier if the queue is unlimited
            for pkt_id in range(pkt_num):
                t_wait = max(0., t_sojrn - self.iats[pkt_id])
                t_sojrn = t_wait + srv_durs[pkt_id]
                waits.append(t_wait)

        else:
            cum_backlog_srv_durs = np.array([0.])
            for pkt_id in range(pkt_num):
                t_wait = max(0., t_sojrn - self.iats[pkt_id])
                q_len = np.argmax(t_wait <= cum_backlog_srv_durs)

                if q_len < self.q_cap:
                    srv_dur = srv_durs[pkt_id]
                    t_sojrn = t_wait + srv_dur
                    cum_backlog_srv_durs = np.insert(cum_backlog_srv_durs[:q_len+1] + srv_dur, 0, srv_dur)
                    waits.append(t_wait)

                else:
                    t_sojrn = t_wait
                    waits.append(np.inf)

        self.waits = np.asarray(waits)
        self.srv_durs = srv_durs
        self.dprt_times = self.arvl_times + self.waits + srv_durs
        self.pkt_sizes = pkt_sizes
        self.pkt_num = pkt_num
    # End of `compute_departure_times`

    def compute_system_events(self):
        self.compute_departure_times()
        
        event_times = np.hstack((self.arvl_times, self.dprt_times))

        sys_changes = np.hstack((np.ones(self.pkt_num), -np.ones(self.pkt_num)))
        sys_changes[:self.pkt_num][np.isinf(self.dprt_times)] = 0.

        event_types = np.asarray(['arvl']*self.pkt_num + ['dprt']*self.pkt_num)

        sort_idc = np.argsort(event_times)
        event_times = event_times[sort_idc]

        event_num = (event_times <= self.t_limit).sum()

        self.event_times = event_times[:event_num]
        self.sys_changes = sys_changes[sort_idc][:event_num]
        self.sys_states = self.sys_changes.cumsum()
        self.event_types = event_types[sort_idc][:event_num]
        self.inc_pkt_ids = sort_idc[:event_num] % self.pkt_num
    # End of method `compute_system_events`

    def save_simulation_results(self):
        print('\nSaving simulation trace... ', end='', flush=True)
        # Store event list
        event_df = pd.DataFrame({   'event id': np.arange(len(self.event_times)),
                                    'timestamp (s)': self.event_times,
                                    'type': self.event_types,
                                    'incident packet': self.inc_pkt_ids,
                                    'system state': self.sys_states}).set_index('event id')

        trace_dir = os.path.join(os.path.dirname(__file__), 'simtrace')

        try: os.mkdir(trace_dir)
        except FileExistsError: pass

        file_path = os.path.join(trace_dir, 'events.csv')
        try: event_df.to_csv(file_path)
        except PermissionError as err:
            print(f'\nError!!! Failed to save simulation trace to "{file_path}".')
            print('Make sure this file is not being opened.')
            return

        # Store packet list
        pkt_df = pd.DataFrame({ 'packet id': np.arange(self.pkt_num),
                                'size (bytes)': self.pkt_sizes,
                                'arrive (s)': self.arvl_times,
                                'depart (s)': self.dprt_times,
                                'wait (ms)': 1000.*self.waits}).set_index('packet id')

        file_path = os.path.join(trace_dir, 'packets.csv')

        try: pkt_df.to_csv(file_path)
        except PermissionError as err:
            print(f'\nError!!! Failed to store simulation trace to "{file_path}".')
            print('Make sure this file is not being opened.')
            return
        print('Done!')
    # End of method `save_simulation_results`

if __name__ == '__main__':
    clscr()
    main()