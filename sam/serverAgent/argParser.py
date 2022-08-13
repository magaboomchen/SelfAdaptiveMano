#!/usr/bin/python
# -*- coding: UTF-8 -*-

import argparse

from sam.base.argParser import ArgParserBase


class ArgParser(ArgParserBase):
    def __init__(self, *args, **kwargs):
        super(ArgParser, self).__init__(*args, **kwargs)
        self.parser = argparse.ArgumentParser(description='Set server agent.', add_help=False)
        self.parser.add_argument('nicPciAddress', metavar='pcia', type=str, 
            help='PCI address of the input NIC, e.g. 0000:00:08.0')
        self.parser.add_argument('controllNicName', metavar='cnn', type=str, 
            help='name of control nic, e.g. ens3')
        self.parser.add_argument('serverType', metavar='st', type=str, 
            help='type of server, e.g. nfvi , classifier, tester, normal')
        self.parser.add_argument('datapathNicIP', metavar='dni', type=str, 
            help='ip of datapath nic, e.g. 2.2.0.35')
        self.parser.add_argument('serverID', metavar='sID', type=int, 
            help='serverID, e.g. 10001') 
        self.parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS,
                            help='Show this help message and exit. Example usage: python serverAgent.py 0000:00:08.0 ens3 classifier 2.2.0.34 serverID 10001')
        self.args = self.parser.parse_args()