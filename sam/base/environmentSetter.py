#!/usr/bin/python
# -*- coding: UTF-8 -*-

import site
import os
import subprocess


class EnvironmentSetter(object):
    def __init__(self):
        pass

    def addPythonModule2SystemPath(self,path, pthfileName="selfAdaptiveMano.pth"):
        directorys = site.getsitepackages()
        # ['/usr/local/lib/python2.7/dist-packages',
        #  '/usr/lib/python2.7/dist-packages']
        for direct in directorys:
            try:
                shellCmd = "sudo sh -c 'echo  " + path + " > " \
                    + direct + "/" + pthfileName + "'"
                subprocess.check_output([shellCmd], shell=True)
            except:
                pass
        # echo XXX > /usr/local/lib/python2.7/dist-packages/selfAdaptiveMano.pth
        # echo XXX > /usr/lib/python2.7/dist-packagesselfAdaptiveMano.pth


if __name__=="__main__":
    eS = EnvironmentSetter()
    thisModuleAbsPath = os.path.abspath(__file__)
    thisModuleAbsPath = thisModuleAbsPath.replace("/sam/base/environmentSetter.py"," ")
    eS.addPythonModule2SystemPath(thisModuleAbsPath)