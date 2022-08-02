#!/usr/bin/python
# -*- coding: UTF-8 -*-

import os
import shutil
import logging

from sam.base.exceptionProcessor import ExceptionProcessor
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.orchestration import orchestrator
from sam.mediator import mediator
from sam.measurement import measurer
from sam.serverController.classifierController import classifierControllerCommandAgent
from sam.serverController.sffController import sffControllerCommandAgent
from sam.serverController.vnfController import vnfController
from sam.serverController.serverManager import serverManager


def getFileDirectory(filePath):
    index = filePath.rfind('/')
    directoryPath = filePath[0:index]
    return directoryPath

def delDirectory(directoryPath):
    if os.path.exists(directoryPath):
        shutil.rmtree(directoryPath)
    else:
        print("The direcoty {0} does not exist".format(directoryPath))

def cleanAllLogFile():
    logConfigur = LoggerConfigurator(__name__, './log',
        'cleanAllLogFile.log', level='info')
    logger = logConfigur.getLogger()

    fileList = [
        orchestrator.__file__,
        measurer.__file__,
        mediator.__file__,
        sffControllerCommandAgent.__file__,
        classifierControllerCommandAgent.__file__,
        vnfController.__file__,
        serverManager.__file__
    ]

    for filePath in fileList:
        try:
            directoryPath = getFileDirectory(filePath)
            logger.info("clean logs:" + directoryPath + "/log/")
            logDirectory = "{0}/log/".format(directoryPath)
            delDirectory(logDirectory)
        except Exception as ex:
            ExceptionProcessor(logger).logException(ex)

    try:
        directoryPath = getFileDirectory(orchestrator.__file__)
        logger.info("clean logs:" + directoryPath + "/test/integrate/log")
        logDirectory = "{0}/test/integrate/log".format(directoryPath)
        delDirectory(logDirectory)
    except Exception as ex:
        ExceptionProcessor(logger).logException(ex)

if __name__ == "__main__":
    cleanAllLogFile()