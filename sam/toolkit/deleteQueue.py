#!/usr/bin/python
# -*- coding: UTF-8 -*-

import sys

from sam.base.shellProcessor import ShellProcessor


if __name__ == "__main__":
    sP = ShellProcessor()
    res = sP.runShellCommand("sudo rabbitmqctl list_queues")
    if sys.version > '3':
        res = res.strip().split('\\n')
    else:
        res = res.strip().split('\n')
    for idx,line in enumerate(res):
        if idx>=3:
            line = line.split()
            queueName = line[0]
            print("queueName is {0}".format(queueName))
            messageNum = int(line[1])
            try:
                sP.runShellCommand(
                    "sudo rabbitmqctl delete_queue {0}".format(queueName))
            except:
                pass