#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.argParser import *


class ArgParser(ArgParserBase):
    def __init__(self, *args, **kwargs):
        super(ArgParser, self).__init__(*args, **kwargs)
        self.parser = argparse.ArgumentParser(description='Set Orchestrator.', add_help=False)
        self.parser.add_argument('-name', metavar='Orchestration Name', type=str, 
            default=None, help='orchestration Name, e.g. 1')
        self.parser.add_argument("-turnOff", action="store_true",
            help='Turn Orchestration Off')
        self.parser.add_argument('-p', metavar='podNumber',
            type=int, nargs='?', const=1, default=None,
            help="pod number")
        self.parser.add_argument('-minPIdx', metavar='min pod idx',
            type=int, nargs='?', const=1, default=None,
            help="min pod idx")
        self.parser.add_argument('-maxPIdx', metavar='max pod idx',
            type=int, nargs='?', const=1, default=None,
            help="max pod idx")
        self.parser.add_argument('-topoType', metavar='topoType',
            type=str, default=None, help="topology type")
        self.parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS,
                            help='Show this help message and exit. Example usage: python orchestrator.py')
        self.args = self.parser.parse_args()