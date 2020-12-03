#!/usr/bin/python
# -*- coding: UTF-8 -*-

import subprocess
import time

from sam.base.shellProcessor import ShellProcessor
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.serverController.vnfController.vcConfig import vcConfig
from sam.base.exceptionProcessor import ExceptionProcessor


class DockerConfigurator(object):
    def __init__(self):
        logConfigur = LoggerConfigurator(__name__, './log',
            'dockerConfigurator.log', level='info')
        self.logger = logConfigur.getLogger()
        self.sP = ShellProcessor()
        self.checkOperateSystem()

    def checkOperateSystem(self):
        results = self.sP.runShellCommand("cat /proc/version")
        if results.find("ubuntu") == -1:
            raise ValueError("Only support ubuntu system!")

    def configDockerListenPort(self, listenPort=vcConfig.DOCKER_TCP_PORT):
        try:
            self.sP.runShellCommand(
                "sudo mkdir /etc/systemd/system/docker.service.d")
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex,
                " configDockerListenPort ")

        try:
            self.sP.runShellCommand(
                "sudo -- bash -c 'cat /dev/null > /etc/systemd/system/docker.service.d/tcp.conf'")
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex,
                " configDockerListenPort ")

        command = "sudo -- bash -c 'cat > /etc/systemd/system/docker.service.d/tcp.conf <<EOF\n" \
        + "[Service]\n" \
        + "ExecStart=\n" \
        + "ExecStart=/usr/bin/dockerd -H unix:///var/run/docker.sock -H tcp://0.0.0.0:" + str(listenPort) +"\n" \
        + "EOF'"

        try:
            self.sP.runShellCommand(command)
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex,
                " configDockerListenPort ")

        try:
            self.sP.runShellCommand("sudo systemctl daemon-reload")
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex,
                " configDockerListenPort ")

        try:
            self.sP.runShellCommand("sudo systemctl restart docker")
            
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex,
                " configDockerListenPort ")

        results = self.sP.runShellCommand("ps aux |grep dockerd")
        self.logger.info("check docker port:\n{0}".format(results))
