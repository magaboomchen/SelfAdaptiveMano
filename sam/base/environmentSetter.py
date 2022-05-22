#!/usr/bin/python
# -*- coding: UTF-8 -*-

import site
import os
import pwd
import json
import subprocess
import argparse

from sam.base.argParser import ArgParserBase


class ArgParser(ArgParserBase):
    def __init__(self, *args, **kwargs):
        super(ArgParser, self).__init__(*args, **kwargs)
        self.parser = argparse.ArgumentParser(description='Set server agent.', add_help=False)
        self.parser.add_argument('ip', metavar='rIP', type=str, nargs='?', const=1, default='127.0.0.1',
            help="rabbitMqServerIP")
        self.parser.add_argument('user', metavar='rUser', type=str, nargs='?', const=1, default='mq',
            help="rabbitMqServerUser")
        self.parser.add_argument('passwd', metavar='rPasswd', type=str, nargs='?', const=1, default='123456',
            help="rabbitMqServerPasswd")
        self.parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS,
                            help='Example usage: python environmentSetter.py 127.0.0.1 mq 123456')
        self.args = self.parser.parse_args()


class EnvironmentSetter(object):
    def __init__(self):
        pass

    def addPythonModuleSystemPath(self,path, pthfileName="selfAdaptiveMano.pth"):
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

    def getUsername(self):
        return pwd.getpwuid( os.getuid() )[ 0 ]

    def setRabbitMQConf(self, rabbitMqServerIP, rabbitMqServerUser, rabbitMqServerPasswd):
        filePath = __file__.split("/environmentSetter.py")[0] + '/rabbitMQConf.json'
        confDict = {
            "RABBITMQSERVERIP": rabbitMqServerIP,
            "RABBITMQSERVERUSER": rabbitMqServerUser,
            "RABBITMQSERVERPASSWD": rabbitMqServerPasswd
        }
        with open(filePath, 'w') as jsonfile:
            json.dump(confDict, jsonfile)


if __name__=="__main__":
    argParser = ArgParser()
    rabbitMqServerIP = argParser.getArgs()['ip']
    rabbitMqServerUser = argParser.getArgs()['user']
    rabbitMqServerPasswd = argParser.getArgs()['passwd']

    eS = EnvironmentSetter()
    thisModuleAbsPath = os.path.abspath(__file__)
    thisModuleAbsPath = thisModuleAbsPath.replace("/sam/base/environmentSetter.py"," ")
    eS.addPythonModuleSystemPath(thisModuleAbsPath)
    eS.setRabbitMQConf(rabbitMqServerIP, rabbitMqServerUser, rabbitMqServerPasswd)