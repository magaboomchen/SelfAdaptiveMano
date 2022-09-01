#!/usr/bin/python
# -*- coding: UTF-8 -*-

from logging import Logger

from sam.base.command import CommandReply
from sam.base.messageAgent import MessageAgent
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.orchestration.orchInfoBaseMaintainer import OrchInfoBaseMaintainer
from sam.regulator.scaling.sfcScalingProcessor import SFCScalingProcessor


class ReplyHandler(object):
    def __init__(self, logger, msgAgent, oib):
        # type: (Logger, MessageAgent, OrchInfoBaseMaintainer) -> None
        self.logger = logger
        self.sfcScalingProcessor = SFCScalingProcessor(msgAgent, oib)

    def handle(self, reply):
        # type: (CommandReply) -> None
        try:
            self.logger.info("Get a reply")
            self.sfcScalingProcessor.scalingHandler(reply)
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex, 
                "Regualtor reply handler")
        finally:
            pass
