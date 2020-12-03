#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging

from sam.base.shellProcessor import *
from sam.base.exceptionProcessor import ExceptionProcessor
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

if __name__ == "__main__":
    fileList = [
        orchestrator.__file__,
        measurer.__file__,
        mediator.__file__,
        sffControllerCommandAgent.__file__,
        classifierControllerCommandAgent.__file__,
        vnfController.__file__,
        serverManager.__file__
    ]

    sP = ShellProcessor()

    for filePath in fileList:
        try:
            directoryPath = getFileDirectory(filePath)
            logging.info("clean logs:" + directoryPath + "/log/")
            sP.runShellCommand("sudo rm -rf " + directoryPath + "/log/")
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex)

    try:
        directoryPath = getFileDirectory(orchestrator.__file__)
        logging.info("clean logs:" + directoryPath + "/test/integrate/log")
        sP.runShellCommand("sudo rm -rf " + directoryPath
            + "/test/integrate/log")
    except Exception as ex:
        ExceptionProcessor(self.logger).logException(ex)
