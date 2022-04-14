#!/usr/bin/python
# -*- coding: UTF-8 -*-

import os

from sam.base.exceptionProcessor import ExceptionProcessor
from sam.base.loggerConfigurator import LoggerConfigurator


def mkdirs(dirPath):
    logConfigur = LoggerConfigurator("mkdirs", './log',
        'mkdirs.log', level='debug')
    logger = logConfigur.getLogger()
    try:
        os.makedirs(dirPath)
    except Exception as ex:
        if str(ex).find("17") == -1:
            ExceptionProcessor(logger).logException(ex)
