#!/usr/bin/python
# -*- coding: UTF-8 -*-

import argparse

from sam.base.argParser import ArgParserBase
from sam.base.sshAgent import SSHAgent
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.compatibility import SAM_MODULE_ABS_PATH
from sam.dispatcher.test.testConfig import PRIVATE_KEY_FILE_PATH, RABBITMQ_SERVER_IP


class ArgParser(ArgParserBase):
    def __init__(self, *args, **kwargs):
        super(ArgParser, self).__init__(*args, **kwargs)
        self.parser = argparse.ArgumentParser(description='Set QueueCleaner.', add_help=False)
        self.parser.add_argument('-password', metavar='pw', type=str, 
            default=None, help='Password')
        self.parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS,
                            help='Show this help message and exit.')
        self.args = self.parser.parse_args()


class QueueCleaner(object):
    def __init__(self, password):
        logConfigur = LoggerConfigurator(__name__, './log',
            'QueueCleaner.log', level='debug')
        self.logger = logConfigur.getLogger()

        self.sA = SSHAgent()
        self.sshUsrname = "smith"
        self.privateKeyFilePath = PRIVATE_KEY_FILE_PATH
        self.remoteIP = RABBITMQ_SERVER_IP
        self.sA.connectSSHWithRSA(self.sshUsrname, self.privateKeyFilePath, self.remoteIP, remoteSSHPort=22)
        self.sA.loadUserPassword(password)
        resDict = self.sA.runShellCommandWithSudo("python {0}/toolkit/clearAllSAMQueue.py".format(SAM_MODULE_ABS_PATH))

        data = resDict['stdout'].read().decode("utf-8")
        self.logger.info(data)


if __name__ == "__main__":
    argParser = ArgParser()
    password = argParser.getArgs()['password']
    qc = QueueCleaner(password)
