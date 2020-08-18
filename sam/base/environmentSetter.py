import site
import os
import pwd
import subprocess
import argparse
from argParser import *
from shellProcessor import *

class ArgParser(ArgParserBase):
    def __init__(self, *args, **kwargs):
        super(ArgParser, self).__init__(*args, **kwargs)
        self.parser = argparse.ArgumentParser(description='Set project path.',
            add_help=False)
        self.parser.add_argument('path', metavar='path', type=str, 
            help='project path')
        self.parser.add_argument('-h', '--help', action='help',
            default=argparse.SUPPRESS,
            help='Show this help message and exit. Example usage: python environmentSetting.py /home/smith/HaoChen/Project/SelfAdaptiveMano/')
        self.args = self.parser.parse_args()

class EnvironmentSetter(object):
    def __init__(self):
        self.sP = ShellProcessor()

    def addSAMSystemPath(self,path):
        directorys = site.getsitepackages()
        print(directorys)
        for direct in directorys:
            self.sP.runShellCommand(
                "echo  '" + selfAdaptiveManoFilePath + "' > " + \
                direct + "/selfAdaptiveMano.pth")

    def getUsername():
        return pwd.getpwuid( os.getuid() )[ 0 ]

if __name__=="__main__":
    aP = ArgParser()
    arg = aP.getArgs()
    selfAdaptiveManoFilePath = arg['path']
    eS = EnvironmentSetter()
    eS.addSAMSystemPath(selfAdaptiveManoFilePath)