#!/usr/bin/python
# -*- coding: UTF-8 -*-

import subprocess
import logging

import psutil

from sam.base.compatibility import x2str
from sam.base.loggerConfigurator import LoggerConfigurator


class ShellProcessor(object):
    def __init__(self):
        logging.getLogger("psutil").setLevel(logging.ERROR)
        logConfigur = LoggerConfigurator(__name__, './log',
            'shellProcessor.log', level='warning')
        self.logger = logConfigur.getLogger()

    def listRunningProcess(self):
        self.logger.info("List running process.")
        for p in psutil.process_iter(attrs=['pid', 'name']):
            self.logger.info(p)

    def isProcessRun(self,processName):
        for p in psutil.process_iter(attrs=['pid', 'name']):
            if processName in p.info['name']:
                self.logger.info(processName + " has already running.")
                return True
        return False

    def runProcess(self,filePath, root=False):
        if root == True:
            user = "sudo "
        else:
            user = ""
        out_bytes = subprocess.check_output(
            [ user + filePath], shell=True)

    def getProcessCPUAndMemoryUtilization(self, pid, interval=1):
        p = psutil.Process(pid)
        cpuUtilList = p.cpu_percent(interval=interval)
        memoryUtilList = p.memory_info().rss
        return cpuUtilList, memoryUtilList

    def killProcess(self,processName):
        for p in psutil.process_iter(attrs=['pid', 'name']):
            if processName in p.info['name']:
                pid = int(p.info['pid'])
                out_bytes = subprocess.check_output(
                    ["sudo kill " + str(pid)], shell=True)

    def isPythonScriptRun(self,moduleName):
        for p in psutil.process_iter(attrs=['pid', 'name', 'cmdline']):
            self.logger.info(p)
            if p.info['name'] == "python":
                for cmdline in p.info['cmdline']:
                    if cmdline.count(moduleName) > 0:
                        return True
        return False

    def runPythonScript(self, filePath, root=False, cmdPrefix="", cmdSuffix=""):
        if root == True:
            user = 'sudo env "PATH=$PATH" '
        else:
            user = ""
        subprocess.Popen(
            [ user + "{0} python {1} {2}".format(cmdPrefix, filePath, cmdSuffix)], shell=True)

    def getPythonScriptProcessPid(self, scriptName):
        for p in psutil.process_iter(attrs=['pid', 'name', 'cmdline']):
            if p.info['name'] == "python":
                cmdline = " ".join(p.info['cmdline'])
                self.logger.debug("cmdline:{0}".format(cmdline))
                self.logger.debug("scriptName:{0}".format(scriptName))
                if cmdline.find(scriptName) != -1:
                    self.logger.debug(p.info['pid'])
                    return p.info['pid']
        return None

    def killPythonScript(self,moduleName):
        for p in psutil.process_iter(attrs=['pid', 'name', 'cmdline']):
            if p.info['name'] == "python":
                for cmdline in p.info['cmdline']:
                    if cmdline.find(moduleName) != -1:
                        pid = int(p.info['pid'])
                        out_bytes = subprocess.check_output(
                            ["sudo kill " + str(pid)], shell=True)
    
    def runShellCommand(self,shellCmd):
        res = subprocess.check_output([shellCmd], shell=True)
        return x2str(res)