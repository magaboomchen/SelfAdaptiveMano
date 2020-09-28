#!/usr/bin/python
# -*- coding: UTF-8 -*-

import subprocess
import logging
import time

from sam.serverController.vnfController.vnfController import *
from sam.base.shellProcessor import ShellProcessor


class DockerConfigurator(object):
    def __init__(self):
        self.sP = ShellProcessor()
        self.checkOperateSystem()

    def checkOperateSystem(self):
        results = self.sP.runShellCommand("cat /proc/version")
        if results.find("ubuntu") == -1:
            raise ValueError("Only support ubuntu system!")

    def configDockerListenPort(self, listenPort=DOCKER_TCP_PORT):
        try:
            self.sP.runShellCommand(
                "sudo mkdir /etc/systemd/system/docker.service.d")
        except Exception as ex:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)

        try:
            self.sP.runShellCommand(
                "sudo -- bash -c 'cat /dev/null > /etc/systemd/system/docker.service.d/tcp.conf'")
        except Exception as ex:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)

        command = "sudo -- bash -c 'cat > /etc/systemd/system/docker.service.d/tcp.conf <<EOF\n" \
        + "[Service]\n" \
        + "ExecStart=\n" \
        + "ExecStart=/usr/bin/dockerd -H unix:///var/run/docker.sock -H tcp://0.0.0.0:" + str(listenPort) +"\n" \
        + "EOF'"

        try:
            self.sP.runShellCommand(command)
        except Exception as ex:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)

        try:
            self.sP.runShellCommand("sudo systemctl daemon-reload")
        except Exception as ex:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)

        try:
            self.sP.runShellCommand("sudo systemctl restart docker")
            
        except Exception as ex:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)

        results = self.sP.runShellCommand("ps aux |grep dockerd")
        logging.info("check docker port:\n{0}".format(results))
