#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.shellProcessor import *


def killAllSAMPythonScripts():
    sP = ShellProcessor()
    sP.killPythonScript("measurer.py")
    sP.killPythonScript("mediator.py")
    sP.killPythonScript("orchestrator.py")
    sP.killPythonScript("ryu")
    sP.killPythonScript("serverAgent.py")
    sP.killPythonScript("serverManager.py")
    sP.killPythonScript("classifierControllerCommandAgent.py")
    sP.killPythonScript("sffControllerCommandAgent.py")
    sP.killPythonScript("vnfController.py")
    sP.killPythonScript("simulator.py")

if __name__ == "__main__":
    killAllSAMPythonScripts()