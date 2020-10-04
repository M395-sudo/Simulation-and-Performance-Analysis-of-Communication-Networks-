'''
File name: dscp_catalog.py
Author: Nguyen Tuan Khai
Date created: 14/04/2020
'''

from enum import Enum
__all__ = ['PHB', 'get_PHB_from_DSCP']

class PHB(Enum):
    EF, AF41, AF42, AF43, AF31, AF32, AF33, AF21, AF22, AF23, AF11, AF12, AF13, BE = \
    0 , 1   , 2   , 3   , 4   , 5   , 6   , 7   , 8   , 9   , 10  , 11  , 12  , 13

PHB_From_DSCP = {
    0: PHB.BE,
    14: PHB.AF13,
    12: PHB.AF12,
    10: PHB.AF11,
    22: PHB.AF23,
    20: PHB.AF22,
    18: PHB.AF21,
    30: PHB.AF33,
    28: PHB.AF32,
    26: PHB.AF31,
    38: PHB.AF43,
    36: PHB.AF42,
    34: PHB.AF41,
    46: PHB.EF
}

# DSCP --> [Queue]
def get_PHB_from_DSCP(dscp):
    # DSCP is 6 bits, mask out all others
    # 0x3f = 111111, AND: 1&1=1, -=0
    dscp = (dscp & 0x3f)

    return PHB_From_DSCP.get(dscp, PHB.BE)