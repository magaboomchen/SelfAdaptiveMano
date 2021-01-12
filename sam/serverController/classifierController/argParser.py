#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.argParser import *


class ArgParser(ArgParserBase):
    def __init__(self, *args, **kwargs):
        super(ArgParser, self).__init__(*args, **kwargs)
        self.parser = argparse.ArgumentParser(description='Set server agent.', add_help=False)
        self.parser.add_argument('zoneName', metavar='pcia', type=str, nargs='?', const=1, default='',
            help="the name of zone, default: ''")
        self.parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS,
                            help='Example usage: python classifierControllerCommandAgent.py MININET_ZONE or python classifierControllerCommandAgent.py')
        self.args = self.parser.parse_args()