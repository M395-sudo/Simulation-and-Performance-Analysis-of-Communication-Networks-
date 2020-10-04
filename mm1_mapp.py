'''
File name: mm1_mapp.py
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
    sim_time_limit            = 60        # seconds
    queue_capacity            = np.inf    # packets
    mean_inter_arrival_times  = []    # seconds
    mean_pkt_sizes            = []    # Bytes
    out_rate                  =     # bps

    simulator = MM1_Sim(t_limit=sim_time_limit,
                        q_cap=queue_capacity,
                        mean_IATs=mean_inter_arrival_times,
                        mean_pkt_SIZEs=mean_pkt_sizes,
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

    def __init__(self, t_limit, q_cap, mean_IATs, mean_pkt_SIZEs, out_rate):
        self.t_limit = t_limit
        self.q_cap = q_cap
        self.mean_IATs = np.asarray(mean_IATs)
        self.mean_pkt_SIZEs = np.asarray(mean_pkt_SIZEs)
        self.out_rate = out_rate
        self.app_num = len(mean_IATs)
        
        assert self.app_num==len(mean_pkt_SIZEs), f"Error!!! Numbers of mean IATs and Pkt Sizes don't match."

    # End of class constructor

    def generate_arrival_times(self):
        # Pre-estimate number of arrivals
        LAMBs = self.t_limit/self.mean_IATs
            # 3.29 below is just a heuristic number
        arvl_NUMs = np.ceil(LAMBs + 3.29*LAMBs**.5).astype(np.int0)

        self.IATs, self.arvl_TIMEs = [], []

        for mean_iat, arvl_num in zip(self.mean_IATs, arvl_NUMs):
            iats = generate_rand_iats_in_sec(mean_iat, arvl_num)
            while iats.sum() < self.t_limit:
                iats = np.concatenate((iats, generate_rand_iats_in_sec(mean_iat, arvl_num)))

            arvl_times = iats.cumsum()
            self.IATs.append(iats[(msk:= arvl_times<=self.t_limit)])
            self.arvl_TIMEs.append(arvl_times[msk])
    # End of method `generate_arrival_times`

    def compute_departure_times(self):
        pkt_NUMs = list(map(len, self.arvl_TIMEs))

        pkt_SIZEs = list(map(lambda arg: np.ceil(generate_rand_pkt_sizes_in_byte(*arg)), zip(self.mean_pkt_SIZEs, pkt_NUMs)))
        srv_DURs = [get_srv_durations_in_sec(pkt_sizes, self.out_rate) for pkt_sizes in pkt_SIZEs]

        # Aggregate arrival times
        ag_arvl_times = np.hstack(self.arvl_TIMEs)
        ag_arvl_times = ag_arvl_times[(sort_idc:=np.argsort(ag_arvl_times))]

        # Aggregate iats
        ag_iats = np.diff(ag_arvl_times, prepend=0.)

        # Aggregate sds, pkt sizes, app ids
        ag_srv_durs, ag_pkt_sizes, ag_app_ids = \
                np.vstack(( np.hstack(srv_DURs)[sort_idc],
                            np.hstack(pkt_SIZEs)[sort_idc],
                            np.repeat(np.arange(self.app_num), pkt_NUMs) ))[:, sort_idc]

        # How many packets are generated in total?
        ag_pkt_num = sum(pkt_NUMs)
        
        t_wait, t_sojrn = 0., 0.
        ag_waits = []

        if self.q_cap == np.inf:
            # It's easier if the queue is unlimited
            for pkt_id in range(ag_pkt_num):
                t_wait = max(0., t_sojrn - ag_iats[pkt_id])
                t_sojrn = t_wait + ag_srv_durs[pkt_id]
                ag_waits.append(t_wait)

        else:
            cum_backlog_srv_durs = np.array([0.])
            for pkt_id in range(ag_pkt_num):
                t_wait = max(0., t_sojrn - ag_iats[pkt_id])
                q_len = np.argmax(t_wait <= cum_backlog_srv_durs)

                if q_len < self.q_cap:
                    srv_dur = ag_srv_durs[pkt_id]
                    t_sojrn = t_wait + srv_dur
                    cum_backlog_srv_durs = np.insert(cum_backlog_srv_durs[:q_len+1] + srv_dur, 0, srv_dur)
                    ag_waits.append(t_wait)

                else:
                    t_sojrn = t_wait
                    ag_waits.append(np.inf)

        self.ag_waits = np.asarray(ag_waits)
        self.ag_srv_durs = ag_srv_durs
        self.ag_arvl_times = ag_arvl_times
        self.ag_dprt_times = ag_arvl_times + self.ag_waits + ag_srv_durs
        self.ag_pkt_sizes = ag_pkt_sizes
        self.ag_app_ids = ag_app_ids
        self.ag_pkt_num = ag_pkt_num
    # End of `compute_departure_times`

    def compute_system_events(self):
        self.compute_departure_times()
        
        event_times = np.hstack((self.ag_arvl_times, self.ag_dprt_times))

        sys_changes = np.hstack((np.ones(self.ag_pkt_num), -np.ones(self.ag_pkt_num)))
        sys_changes[:self.ag_pkt_num][np.isinf(self.ag_dprt_times)] = 0.

        event_types = np.asarray(['arvl']*self.ag_pkt_num + ['dprt']*self.ag_pkt_num)

        sort_idc = np.argsort(event_times)
        event_times = event_times[sort_idc]

        event_num = (event_times <= self.t_limit).sum()

        self.event_times = event_times[:event_num]
        self.sys_changes = sys_changes[sort_idc][:event_num]
        self.sys_states = self.sys_changes.cumsum()
        self.event_types = event_types[sort_idc][:event_num]
        self.inc_pkt_ids = sort_idc[:event_num] % self.ag_pkt_num
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
        pkt_df = pd.DataFrame({ 'packet id': np.arange(self.ag_pkt_num),
                                'app id': self.ag_app_ids,
                                'size (bytes)': self.ag_pkt_sizes,
                                'arrive (s)': self.ag_arvl_times,
                                'depart (s)': self.ag_dprt_times,
                                'wait (ms)': 1000.*self.ag_waits}).set_index('packet id')

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