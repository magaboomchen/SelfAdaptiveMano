#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.argParser import *


class SamSimulationArgParser(ArgParserBase):
    def __init__(self, *args, **kwargs):
        super(SamSimulationArgParser, self).__init__(*args, **kwargs)
        self.parser = argparse.ArgumentParser(
            description='help message.',
            add_help=False)
        self.parser.add_argument('-e', metavar='expNum',
            type=int, nargs='?', const=1, default='0',
            help="experiment number")
        self.parser.add_argument('-topo', metavar='topologyType',
            type=str, nargs='?', const=1, default=None,
            help="topology type")
        self.parser.add_argument('-p', metavar='podNumber',
            type=int, nargs='?', const=1, default="4",
            help="pod number")
        self.parser.add_argument('-sl', metavar='sfcLength',
            type=int, nargs='?', const=1, default="5",
            help="sfc length")
        self.parser.add_argument('-nPoPNum', metavar='nPoPNum',
            type=int, nargs='?', const=1, default="6",
            help="NFV PoP number")
        self.parser.add_argument('-intNum', metavar='intNum',
            type=int, nargs='?', const=1, default="6",
            help="intermediate node number")
        self.parser.add_argument('-aggNum', metavar='aggNum',
            type=int, nargs='?', const=1, default="6",
            help="aggregate node number")
        self.parser.add_argument('-torNum', metavar='torNum',
            type=int, nargs='?', const=1, default="3",
            help="tor node number")
        self.parser.add_argument('-enlargeTimes', metavar='enlargeTimes',
            type=int, nargs='?', const=1, default="1",
            help="enlarge times")
        self.parser.add_argument('-taskType', metavar='taskType',
            type=str, nargs='?', const=1, default="Normal",
            help="task Type")
        self.parser.add_argument('-h', '--help', action='help',
                            default=argparse.SUPPRESS,
                            help="fast re-route help message")
        self.args = self.parser.parse_args()
