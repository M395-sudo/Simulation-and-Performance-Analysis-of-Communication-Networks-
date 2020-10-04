'''
File name: tmp_stats.py
Author: Nguyen Tuan Khai
Date created: 14/04/2020
'''

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import numpy as np, pandas as pd

def main():
    results_dir = os.path.join(os.path.dirname(__file__), 'results')
    tmp_df = pd.read_csv(os.path.join(results_dir, 'tmp_result.csv')).replace(np.inf, np.nan).dropna()

    print(tmp_df.describe())

if __name__ == '__main__':
    main()