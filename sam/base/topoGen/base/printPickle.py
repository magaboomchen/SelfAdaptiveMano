#!/usr/bin/python
# -*- coding: UTF-8 -*-

import pprint
import argparse

from sam.base.argParser import ArgParserBase
from sam.base.pickleIO import PickleIO


class ArgParser(ArgParserBase):
    def __init__(self, *args, **kwargs):
        super(ArgParser, self).__init__(*args, **kwargs)
        self.parser = argparse.ArgumentParser(
            description='help message.',
            add_help=False)
        self.parser.add_argument('-f', metavar='fileName',
            type=str, nargs='?', const=1, default=None, required=True, 
            help="pickle file name")
        self.parser.add_argument('-h', '--help', action='help',
                            default=argparse.SUPPRESS,
                            help="fast re-route help message")
        self.args = self.parser.parse_args()


if __name__ == "__main__":
    argParser = ArgParser()
    fileName = argParser.getArgs()['f']

    pIO = PickleIO()
    stuff = pIO.readPickleFile(fileName)
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(stuff)
