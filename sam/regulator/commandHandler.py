#!/usr/bin/python
# -*- coding: UTF-8 -*-

from logging import Logger

from sam.base.command import CMD_TYPE_HANDLE_FAILURE_ABNORMAL, Command
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.base.messageAgent import MessageAgent
from sam.orchestration.orchInfoBaseMaintainer import OrchInfoBaseMaintainer
from sam.regulator.recovery.sfcRestorer import SFCRestorer


class CommandHandler(object):
    def __init__(self, logger,  # type: Logger
                msgAgent,       # type: MessageAgent
                oib             # type: OrchInfoBaseMaintainer
                ):
        self.logger = logger
        self.sfcRestorer = SFCRestorer(msgAgent, oib)

    def handle(self, cmd):
        # type: (Command) -> None
        try:
            self.logger.info("Get a command reply")
            if cmd.cmdType == CMD_TYPE_HANDLE_FAILURE_ABNORMAL:
                self.sfcRestorer.failureAbnormalHandler(cmd)
            else:
                pass
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex, 
                "Regualtor command handler")
        finally:
            pass
