#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
This file defines the format of rules used for nat. 
In vnfi, NATTuple is maintained in vnfi.config['NAT']
'''

class NATTuple(object):
    def __init__(self, pubIP, minPort, maxPort): 
        self.pubIP = pubIP   # public IP address 
        # range of available port
        self.minPort = minPort  
        self.maxPort = maxPort 