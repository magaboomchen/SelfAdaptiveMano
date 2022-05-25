#!/usr/bin/python
# -*- coding: UTF-8 -*-

# basic settings
MIN_EXP_NUM = 0     # experiments number, just ignore this
MAX_EXP_NUM = 10 # please use shell to run multiple exp simultaneously
VNF_NUM = 15    # VNF type number
SFC_REQUEST_NUM = 100   # ignore this
SERVER_NUM = 20     # server number per ToR switch
SERVER_CLASSIFIER_NUM = 1   # Default is 1, used as the entrance of each SFC
NPOP_NUM = 6    

MIN_SFC_LENGTH = 2
MAX_SFC_LENGTH = 7

# topology
DEFAULT_LINK_LENGTH = 0.001 # unit: km
DEFAULT_LINK_BANDWIDTH = 1  # unit: Gbps
