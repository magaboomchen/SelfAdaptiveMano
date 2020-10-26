#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.shellProcessor import *
from sam.orchestration import orchestrator
from sam.mediator import mediator
from sam.measurement import measurer
from sam.serverController.classifierController import classifierControllerCommandAgent
from sam.serverController.sffController import sffControllerCommandAgent
from sam.serverController.vnfController import vnfController
from sam.serverController.serverManager import serverManager


if __name__ == "__main__":
    sP = ShellProcessor()
    try:
        filePath = orchestrator.__file__
        print(filePath)
        sP.runShellCommand(
            "sudo ls ")
    except:
        pass
