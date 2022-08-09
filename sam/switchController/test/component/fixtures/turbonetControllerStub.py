#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.messageAgent import MessageAgent
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.command import CMD_TYPE_ADD_CLASSIFIER_ENTRY, CMD_TYPE_DEL_CLASSIFIER_ENTRY
from sam.base.messageAgentAuxillary.msgAgentRPCConf import TURBONET_CONTROLLER_IP, \
                                                            TURBONET_CONTROLLER_PORT


class TurbonetControllerStub(object):
    def __init__(self):
        logConfigur = LoggerConfigurator(__name__, './log',
                                         'turbonetControllerStub.log',
                                         level='debug')
        self.logger = logConfigur.getLogger()
        self.logger.info("Init turbonetControllerStub.")

        self._messageAgent = MessageAgent(self.logger)
        self._messageAgent.startMsgReceiverRPCServer(TURBONET_CONTROLLER_IP, 
                                                     TURBONET_CONTROLLER_PORT)

    def recvCmd(self, cmdTypeList, maxCmdCnt):
        try:
            cnt = 0
            while True:
                if cnt == maxCmdCnt:
                    break
                msg = self._messageAgent.getMsgByRPC(TURBONET_CONTROLLER_IP, 
                                                     TURBONET_CONTROLLER_PORT)
                msgType = msg.getMessageType()
                if msgType == None:
                    pass
                else:
                    body = msg.getbody()
                    if self._messageAgent.isCommand(body):
                        cmd = body
                        if cmd.cmdType in cmdTypeList:
                            cnt += 1
                        else:
                            raise ValueError("Unknown cmd type {0}".format(cmd.cmdType))
                    else:
                        self.logger.error(
                            "Unknown massage body:{0}".format(body))
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex, 
                "turbonetControllerStub msg handler")
        finally:
            pass

    # def recvAllAddClassifierEntriesCmd(self, sfc):
    #     try:
    #         cnt = 0
    #         while True:
    #             if cnt == 1:
    #                 break
    #             msg = self._messageAgent.getMsgByRPC(TURBONET_CONTROLLER_IP, 
    #                                                  TURBONET_CONTROLLER_PORT)
    #             msgType = msg.getMessageType()
    #             if msgType == None:
    #                 pass
    #             else:
    #                 body = msg.getbody()
    #                 if self._messageAgent.isCommand(body):
    #                     cmd = body
    #                     if cmd.cmdType in [CMD_TYPE_ADD_CLASSIFIER_ENTRY]:
    #                         cnt += 1
    #                     else:
    #                         raise ValueError("Unknown cmd type {0}".format(cmd.cmdType))
    #                 else:
    #                     self.logger.error(
    #                         "Unknown massage body:{0}".format(body))
    #     except Exception as ex:
    #         ExceptionProcessor(self.logger).logException(ex, 
    #             "turbonetControllerStub msg handler")
    #     finally:
    #         pass

    # def recvAllAddRouteEntriesCmd(self, sfci):
    #     try:
    #         cnt = 0
    #         while True:
    #             if cnt == 1:
    #                 break
    #             msg = self._messageAgent.getMsgByRPC(TURBONET_CONTROLLER_IP, 
    #                                                  TURBONET_CONTROLLER_PORT)
    #             msgType = msg.getMessageType()
    #             if msgType == None:
    #                 pass
    #             else:
    #                 body = msg.getbody()
    #                 if self._messageAgent.isCommand(body):
    #                     cmd = body
    #                     if cmd.cmdType in [CMD_TYPE_ADD_CLASSIFIER_ENTRY]:
    #                         cnt += 1
    #                     else:
    #                         raise ValueError("Unknown cmd type {0}".format(cmd.cmdType))
    #                 else:
    #                     self.logger.error(
    #                         "Unknown massage body:{0}".format(body))
    #     except Exception as ex:
    #         ExceptionProcessor(self.logger).logException(ex, 
    #             "turbonetControllerStub msg handler")
    #     finally:
    #         pass
