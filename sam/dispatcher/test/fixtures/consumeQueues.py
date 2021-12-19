#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.messageAgent import *

class Consumer(object):
    def __init__(self, queueName):
        self.queueName = queueName

        logConfigur = LoggerConfigurator(__name__, './log',
            'Consumer.log', level='debug')
        self.logger = logConfigur.getLogger()

        self._messageAgent = MessageAgent(self.logger)
        self._messageAgent.startRecvMsg(self.queueName)

    def startConsumer(self):
        self.logger.info("start Consume")
        while True:
            time.sleep(0.0001)
            msg = self._messageAgent.getMsg(self.queueName)
            msgType = msg.getMessageType()
            if msgType == None:
                pass
            else:
                body = msg.getbody()
                if self._messageAgent.isRequest(body):
                    self.logger.info("get a request")
                elif self._messageAgent.isCommandReply(body):
                    self.logger.info("get a command")
                elif self._messageAgent.isCommand(body):
                    self.logger.info("get a command reply")
                else:
                    self.logger.error("Unknown massage body:{0}".format(body))


if __name__ == "__main__":
    queueName = "ORCHESTRATOR_QUEUE_0_19"
    c = Consumer(queueName)
    c.startConsumer()
