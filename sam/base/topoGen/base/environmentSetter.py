#!/usr/bin/python
# -*- coding: UTF-8 -*-

import site
import os
import pwd
import subprocess


class EnvironmentSetter(object):
    def __init__(self):
        pass

    def addPythonModuleSystemPath(self,path, pthfileName="samSimulation.pth"):
        directorys = site.getsitepackages()
        print("directorys: {0}".format(directorys))
        # ['/usr/local/lib/python2.7/dist-packages',
        #  '/usr/lib/python2.7/dist-packages']
        for direct in directorys:
            shellCmd = "sudo sh -c 'echo  " + path + " > " \
                + direct + "/" + pthfileName + "'"
            try:
               subprocess.check_output([shellCmd], shell=True)
            except:
                pass
        # echo XXX > /usr/local/lib/python2.7/dist-packages/selfAdaptiveMano.pth
        # echo XXX > /usr/lib/python2.7/dist-packagesselfAdaptiveMano.pth

    def getUsername():
        return pwd.getpwuid( os.getuid() )[ 0 ]

if __name__=="__main__":
    eS = EnvironmentSetter()
    thisModuleAbsPath = os.path.abspath(__file__)
    thisModuleAbsPath = thisModuleAbsPath.replace("/samSimulation/base/environmentSetter.py"," ")
    eS.addPythonModuleSystemPath(thisModuleAbsPath)
