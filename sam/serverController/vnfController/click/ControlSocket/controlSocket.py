#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
demo: Get nagg variable from remote docker container running fastclick
'''

import os 

from sam.base.shellProcessor import ShellProcessor


class ControlSocket(object):
    def __init__(self):
        self.moduleAbsPath = self.getCurrentFileAbsPath()
        self.controlSocketAppDir = self.moduleAbsPath
        # print(self.moduleAbsPath)
        # print(self.controlSocketAppDir)
        self.sP = ShellProcessor()

    def getCurrentFileAbsPath(self):
        filePath = os.path.abspath(__file__)
        idx = filePath.rfind("/")
        return filePath[:idx+1]

    def readStateOfAnElement(self, ipAddr, socketPort, elementName, stateName):
        command = " cd {0} " \
            " && java ControlSocket {1} {2} {3} {4}".format(self.controlSocketAppDir,
                                ipAddr, socketPort, elementName, stateName)
        res = self.sP.runShellCommand(command)
        return res


if __name__ == "__main__":
    # sP = ShellProcessor()
    # res = sP.runShellCommand(" cd /data/smith/Projects/SelfAdaptiveMano/sam/serverController/vnfController/click/ControlSocket && java ControlSocket ipv4_mon_direction0 stat ")
    # assert res == "0\n"
    cS = ControlSocket()