'''
File name: rr.py
Author: Nguyen Tuan Khai
Date created: 14/04/2020
'''

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from aux_.pyaux import *
from dscp_catalog import *
from student.implement import *
import numpy as np
import pandas as pd

def main():
        # Feel free to modify the parameter "sim_time_limit".
    sim_time_limit            = 60        # seconds
    queue_capacity            =     # packets
    mean_inter_arrival_times  = []    # seconds
    mean_pkt_sizes            = []    # Bytes
    dscps                     = []
    out_rate                  =     # bps
    phb_weights               = {   PHB.BE: 1,
                                    PHB.AF13: 1,
                                    PHB.AF12: 1,
                                    PHB.AF11: 1,
                                    PHB.AF23: 1,
                                    PHB.AF22: 1,
                                    PHB.AF21: 1,
                                    PHB.AF33: 1,
                                    PHB.AF32: 1,
                                    PHB.AF31: 1,
                                    PHB.AF43: 1,
                                    PHB.AF42: 1,
                                    PHB.AF41: 1,
                                    PHB.EF: 1
                                }

    simulator = DiffServ_Sim(   t_limit=sim_time_limit,
                                q_cap=queue_capacity,
                                mean_IATs=mean_inter_arrival_times,
                                mean_pkt_SIZEs=mean_pkt_sizes,
                                DSCPs=dscps,
                                phb_WEIs=phb_weights,
                                out_rate=out_rate)

    simulator.simulate()
# End of function `main`

class DiffServ_Sim:

    def simulate(self):
        print('Simulation has started.')
        self.generate_arrival_times()
        self.compute_system_events()
        self.save_simulation_results()
        input('\nPress <Enter> to finish.\n')
    # End of method `simulate`

    def __init__(self, t_limit, q_cap, mean_IATs, mean_pkt_SIZEs, DSCPs, phb_WEIs, out_rate):
        self.t_limit = t_limit
        self.q_cap = q_cap
        self.mean_IATs = np.asarray(mean_IATs)
        self.mean_pkt_SIZEs = np.asarray(mean_pkt_SIZEs)
        self.DSCPs = DSCPs
        self.phb_WEIs = phb_WEIs
        self.out_rate = out_rate
        self.app_num = len(mean_IATs)
        
        assert self.app_num==len(mean_pkt_SIZEs)==len(DSCPs), f"Error!!! Numbers of mean IATs, Pkt Sizes, and DSCPs don't match."
    # End of class constructor

    def compute_system_events(self):
        self.aggregate_and_prepare()

        # Next-event time advancing
        while self.now <= self.t_limit:
            handle_next_event = self.handle_arrival if self.t_arvl_nxt < self.t_dprt_nxt else self.handle_departure
            handle_next_event()

            # Record timestamp
            self.event_times.append(self.now)

            # Record queue lengths
            self.q_LENs.append(q_lens:=list(map(len, self.backlog_srv_DURs)))

            # Record system states
            self.sys_states.append(sum(q_lens) + self.srv_busy)

            # Advance time
            self.now = min(self.t_arvl_nxt, self.t_dprt_nxt)
    # End of method `compute_system_events`

    def handle_arrival(self):
        # Record event type
        self.event_types.append('arvl')

        # Record incident packet
        self.inc_pkt_ids.append(self.arvl_pkt_id)

        # What would be the service duration for this packet?
        srv_dur = self.ag_srv_durs[self.arvl_pkt_id]

        # Which queue does this packet belong to?
        q_id = self.ag_q_ids[self.arvl_pkt_id]

        # Queue up if the server is busy or if the queue runs out of quota
        if self.srv_busy or self.q_QUOTAS[q_id] <= 0:
            # Unless the queue is full, join it
            if len(backlog_srv_durs:=self.backlog_srv_DURs[q_id]) < self.q_cap:
                backlog_srv_durs.append((self.arvl_pkt_id, srv_dur))

        # Get served if the server is free
        else:
            # Now server is busy again
            self.srv_busy = True

            # Schedule the next departure
            self.t_dprt_nxt = self.now + srv_dur
            self.ag_dprt_times[self.arvl_pkt_id] = self.t_dprt_nxt

            # What packet will depart next?
            self.dprt_pkt_id = self.arvl_pkt_id

        # Either way, schedule the next arrival
        self.arvl_pkt_id += 1
        self.t_arvl_nxt = self.ag_arvl_times[self.arvl_pkt_id] \
                                if self.arvl_pkt_id < self.ag_pkt_num \
                                else np.inf
    # End of method `handle_arrival`

    def handle_departure(self):
        # Record event type
        self.event_types.append('dprt')

        # Record incident packet
        self.inc_pkt_ids.append(self.dprt_pkt_id)

        # Check the queue where we left last time first
        for i in range(self.q_num):
            # Which queue to check now?
            q_id = (self.q_id + i) % self.q_num

            # If the queue is empty or runs out of quota, move on to the next queue
            if len(backlog_srv_durs:=self.backlog_srv_DURs[q_id]) == 0 \
                or self.q_QUOTAS[q_id] <= 0: continue

            # Decrement the queue's quota
            self.q_QUOTAS[q_id] -= 1

            # Remember the incumbent queue...
            if self.q_QUOTAS[q_id] > 0: self.q_id = q_id

            # ...or the next queue if it runs out of quota
            else:
                self.q_id = (q_id + 1) % self.q_num

                # Refill quota
                self.q_QUOTAS[q_id] = self.q_WEIs[q_id]

            # Schedule the dext departure
            pkt_id, srv_dur = backlog_srv_durs.pop(0)
            self.t_dprt_nxt = self.now + srv_dur

            # Record departure
            self.ag_dprt_times[pkt_id] = self.t_dprt_nxt

            # What packet will depart next? (for the records only)
            self.dprt_pkt_id = pkt_id

            break

        # If all queues are empty or out of quota, relax the server
        else:
            self.srv_busy = False
            self.t_dprt_nxt = np.inf
    # End of method `handle_departure`

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

    def aggregate_and_prepare(self):
        pkt_NUMs = list(map(len, self.arvl_TIMEs))

        pkt_SIZEs = list(map(lambda arg: np.ceil(generate_rand_pkt_sizes_in_byte(*arg)), zip(self.mean_pkt_SIZEs, pkt_NUMs)))
        srv_DURs = [get_srv_durations_in_sec(pkt_sizes, self.out_rate) for pkt_sizes in pkt_SIZEs]

        phb_VALs = [get_PHB_from_DSCP(dscp).value for dscp in self.DSCPs]

        # Aggregate arrival times
        ag_arvl_times = np.hstack(self.arvl_TIMEs)
        ag_arvl_times = ag_arvl_times[(sort_idc:=np.argsort(ag_arvl_times))]

        # Aggregate sds, pkt sizes, app ids
        ag_srv_durs, ag_pkt_sizes, ag_app_ids, ag_phbs = \
                np.vstack(( np.hstack(srv_DURs)[sort_idc],
                            np.hstack(pkt_SIZEs)[sort_idc],
                            np.repeat(np.arange(self.app_num), pkt_NUMs),
                            np.repeat(phb_VALs, pkt_NUMs) ))[:, sort_idc]

        # How many packets are generated in total?
        ag_pkt_num = sum(pkt_NUMs)

        # Get queue ID base on PHB (PHBs are not necessarily identical to queue IDs)
        q_id_from_phb = np.empty(max(uniq_phbs:=np.unique(phb_VALs)) + 1, np.int0)
        q_id_from_phb[uniq_phbs] = np.arange(q_num:=len(uniq_phbs))

        # Assign aggregate results to class attributes
        self.ag_srv_durs = ag_srv_durs
        self.ag_arvl_times = ag_arvl_times
        self.ag_pkt_sizes = ag_pkt_sizes
        self.ag_app_ids = ag_app_ids.astype(np.int0)
        self.ag_pkt_num = ag_pkt_num
        self.ag_q_ids = q_id_from_phb[ag_phbs.astype(np.int0)]
        self.uniq_phbs = uniq_phbs
        self.q_WEIs = [self.phb_WEIs[PHB(phb)] for phb in uniq_phbs]
        self.q_num = q_num

        # Prepare for events scheduling
        self.event_times = []
        self.event_types = []
        self.inc_pkt_ids = []
        self.sys_states = []
        self.ag_dprt_times = np.full(ag_pkt_num, np.inf)
        self.q_QUOTAS = self.q_WEIs.copy()
        self.q_LENs = []
        self.backlog_srv_DURs = [[] for _ in range(q_num)]
        self.srv_busy = False
        self.arvl_pkt_id = 0
        self.dprt_pkt_id = 0
        self.q_id = 0
        self.t_arvl_nxt = self.ag_arvl_times[0]
        self.t_dprt_nxt = np.inf
        self.now = self.t_arvl_nxt
    # End of `aggregate_and_prepare`

    def save_simulation_results(self):
        print('\nSaving simulation trace... ', end='', flush=True)
        # Store event list
        event_df = pd.DataFrame({   'event id': np.arange(len(self.event_times)),
                                    'timestamp (s)': self.event_times,
                                    'type': self.event_types,
                                    'incident packet': self.inc_pkt_ids,
                                    'system state': self.sys_states}).set_index('event id')

        q_LENs = np.asarray(self.q_LENs)
        for q_id, phb in enumerate(self.uniq_phbs):
            event_df[f'{PHB(phb).name}-q length'] = q_LENs[:, q_id]

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
        waits_millis = (self.ag_dprt_times - self.ag_arvl_times - self.ag_srv_durs)*1000.
        pkt_df = pd.DataFrame({ 'packet id': np.arange(self.ag_pkt_num),
                                'app id': self.ag_app_ids,
                                'size (bytes)': self.ag_pkt_sizes,
                                'arrive (s)': self.ag_arvl_times,
                                'depart (s)': self.ag_dprt_times,
                                'wait (ms)': waits_millis}).set_index('packet id')

        file_path = os.path.join(trace_dir, 'packets.csv')

        try: pkt_df.to_csv(file_path)
        except PermissionError as err:
            print(f'\nError!!! Failed to store simulation trace to "{file_path}".')
            print('Make sure this file is not being opened.')
            return

        # Store apps
        app_df = pd.DataFrame({ 'app id': np.arange(self.app_num),
                                'dscp': np.vectorize(hex)(self.DSCPs)}).set_index('app id')

        file_path = os.path.join(trace_dir, 'apps.csv')

        try: app_df.to_csv(file_path)
        except PermissionError as err:
            print(f'\nError!!! Failed to store simulation trace to "{file_path}".')
            print('Make sure this file is not being opened.')
            return

        print('Done!')
    # End of method `save_simulation_results`

if __name__ == '__main__':
    clscr()
    main()