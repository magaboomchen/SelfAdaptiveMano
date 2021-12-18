#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.argParser import *

class ArgParser(ArgParserBase):
    def __init__(self, *args, **kwargs):
        super(ArgParser, self).__init__(*args, **kwargs)
        self.parser = argparse.ArgumentParser(description='Set Orchestrator.', add_help=False)
        self.parser.add_argument('-idx', metavar='Orchestration Instance Index', type=str, 
            default=None, help='orchestration Instance Index, e.g. 1')
        self.parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS,
                            help='Show this help message and exit. Example usage: python orchestrator.py')
        self.args = self.parser.parse_args()