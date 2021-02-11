#!/usr/bin/python
# -*- coding: UTF-8 -*-

import argparse

from sam.base.loggerConfigurator import LoggerConfigurator


class ArgParserBase(object):
    def __init__(self):
        logConfigur = LoggerConfigurator(__name__, './log',
            'ArgParserBase.log', level='info')
        self.logger = logConfigur.getLogger()

    def getArgs(self):
        return self.args.__dict__
    
    def printArgs(self):
        self.logger.info("argparse.args=",self.args,type(self.args))
        d = self.args.__dict__
        for key,value in d.iteritems():
            self.logger.info('%s = %s'%(key,value))