#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.argParser import *


class ArgParser(ArgParserBase):
    def __init__(self, *args, **kwargs):
        super(ArgParser, self).__init__(*args, **kwargs)
        self.parser = argparse.ArgumentParser(description='Set dispatcher.', add_help=False)
        self.parser.add_argument('-pFilePath', metavar='pifp', type=str, 
            default=None, help='Problem Instance File Path')
        self.parser.add_argument("-localTest", action="store_true",
            help='run local test')
        self.parser.add_argument("-intrinsicTimeModel", action="store_true",
            help='run intrinsic Time Model')
        self.parser.add_argument("-parallelMode", action="store_true",
            help='Parallel Mode')
        self.parser.add_argument('-p', metavar='podNumber',
            type=int, nargs='?', const=1, default=-1,
            help="pod number")
        self.parser.add_argument('-expNum', metavar='expNumber',
            type=int, nargs='?', const=1, default=None,
            help="experiment number")
        self.parser.add_argument('-et', metavar='enlargeTimes',
            type=int, nargs='?', const=1, default=None,
            help="enlarge times")
        self.parser.add_argument('-mappingType', metavar='mappingType',
            type=str, default=None, help="mapping type")
        self.parser.add_argument('-baseSFCNum', metavar='baseSFCNum',
            type=int, nargs='?', const=1, default=None,
            help="baseSFCNum")
        self.parser.add_argument('-topoType', metavar='topoType',
            type=str, default="fat-tree", help="topo type")
        self.parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS,
                            help='Show this help message and exit. Example usage: python dispatcher.py -pFilePath ./test.instance -p 36 ')
        self.args = self.parser.parse_args()