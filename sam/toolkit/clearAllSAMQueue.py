#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.shellProcessor import *

if __name__ == "__main__":
    sP = ShellProcessor()
    try:
        sP.runShellCommand(
            "sudo rabbitmqctl purge_queue MEASURER_QUEUE")
    except:
        pass
    try:
        sP.runShellCommand(
            "sudo rabbitmqctl purge_queue ORCHESTRATOR_QUEUE")
    except:
        pass
    try:
        sP.runShellCommand(
            "sudo rabbitmqctl purge_queue MEDIATOR_QUEUE")
    except:
        pass
    try:
        sP.runShellCommand(
            "sudo rabbitmqctl purge_queue SFF_CONTROLLER_QUEUE")
    except:
        pass
    try:
        sP.runShellCommand(
            "sudo rabbitmqctl purge_queue VNF_CONTROLLER_QUEUE")
    except:
        pass
    try:
        sP.runShellCommand(
            "sudo rabbitmqctl purge_queue SERVER_CLASSIFIER_CONTROLLER_QUEUE")
    except:
        pass
    try:
        sP.runShellCommand(
            "sudo rabbitmqctl purge_queue SERVER_MANAGER_QUEUE")
    except:
        pass
    try:
        sP.runShellCommand(
            "sudo rabbitmqctl purge_queue NETWORK_CONTROLLER_QUEUE")
    except:
        pass
    try:
        sP.runShellCommand(
            "sudo rabbitmqctl purge_queue MININET_TESTER_QUEUE")
    except:
        pass
