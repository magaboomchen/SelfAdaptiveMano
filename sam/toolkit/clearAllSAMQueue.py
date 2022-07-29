#!/usr/bin/python
# -*- coding: UTF-8 -*-

import sys

from sam.base.compatibility import x2str
from sam.base.shellProcessor import ShellProcessor


def clearAllSAMQueue():
    sP = ShellProcessor()
    res = sP.runShellCommand("sudo rabbitmqctl list_queues")
    res = res.strip().split('\n')
    for idx,line in enumerate(res):
        if idx>=3:
            line = line.split('\t')
            if len(line) != 2:
                continue
            queueName = line[0]
            print("queueName is {0}".format(queueName))
            messageNum = int(line[1])
            if messageNum > 0:
                try:
                    sP.runShellCommand(
                        "sudo rabbitmqctl purge_queue {0}".format(queueName))
                except:
                    pass
        else:
            print(line)

if __name__ == "__main__":
    clearAllSAMQueue()