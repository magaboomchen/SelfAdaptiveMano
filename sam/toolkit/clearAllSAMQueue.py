#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
queueList = [
    "REQUEST_PROCESSOR_QUEUE",
    "DCN_INFO_RECIEVER_QUEUE",
    "MEASURER_QUEUE",
    "ORCHESTRATOR_QUEUE",
    "MEDIATOR_QUEUE",
    "SFF_CONTROLLER_QUEUE",
    "SFF_CONTROLLER_QUEUE_PICA8_ZONE",
    "VNF_CONTROLLER_QUEUE",
    "VNF_CONTROLLER_QUEUE_PICA8_ZONE",
    "SERVER_CLASSIFIER_CONTROLLER_QUEUE",
    "SERVER_CLASSIFIER_CONTROLLER_QUEUE_PICA8_ZONE",
    "SERVER_MANAGER_QUEUE",
    "SERVER_MANAGER_QUEUE_PICA8_ZONE",
    "NETWORK_CONTROLLER_QUEUE",
    "NETWORK_CONTROLLER_QUEUE_PICA8_ZONE",
    "MININET_TESTER_QUEUE"
]
'''

from sam.base.shellProcessor import *

if __name__ == "__main__":
    sP = ShellProcessor()
    res = sP.runShellCommand("sudo rabbitmqctl list_queues")
    res = res.strip().split('\n')
    for idx,line in enumerate(res):
        if idx>=3:
            line = line.split()
            queueName = line[0]
            print("queueName is {0}".format(queueName))
            messageNum = int(line[1])
            if messageNum > 0:
                try:
                    sP.runShellCommand(
                        "sudo rabbitmqctl purge_queue {0}".format(queueName))
                except:
                    pass