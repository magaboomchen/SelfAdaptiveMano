#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
This file defines the format of rules used for loadbalancer. 
In vnfi, LBTuple is maintained in vnfi.config['LB']
'''

class LBTuple(object):
    def __init__(self, vip, dst): 
        self.vip = vip   # ip address of the loadbalancer 
        self.dst = dst   # list of dst ip addresses