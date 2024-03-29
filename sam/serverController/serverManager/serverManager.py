#!/usr/bin/python
# -*- coding: UTF-8 -*-

import sys
import time
from typing import Dict
import uuid
import ctypes
import inspect
import threading
import datetime
from packaging import version

from sam.base.server import Server
from sam.base.command import Command, CommandReply, CMD_STATE_SUCCESSFUL, \
    CMD_TYPE_HANDLE_SERVER_STATUS_CHANGE
from sam.base.messageAgent import SAMMessage, MessageAgent, \
    MSG_TYPE_SERVER_REPLY, MSG_TYPE_SERVER_MANAGER_CMD, \
    MSG_TYPE_SERVER_MANAGER_CMD_REPLY, NETWORK_CONTROLLER_QUEUE, \
    MEDIATOR_QUEUE, MSG_TYPE_NETWORK_CONTROLLER_CMD
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.serverController.serverManager.argParser import ArgParser
from sam.base.messageAgentAuxillary.msgAgentRPCConf import SERVER_MANAGER_IP, \
                                                            SERVER_MANAGER_PORT
from sam.serverController.vnfController.sourceAllocator import SourceAllocator

SERVER_TIMEOUT = 10
TIMEOUT_CLEANER_INTERVAL = 5
SERVERID_OFFSET = 10001
SERVER_FAILURE_NOTIFICATION = False

threadLock = threading.Lock()


class SeverManager(object):
    def __init__(self, zoneName=""):
        logConfigur = LoggerConfigurator(__name__, './log',
            'serverManager.log', level='debug')
        self.logger = logConfigur.getLogger()
        self.logger.info('Init ServerManager')
        self.zoneName = zoneName

        self._messageAgent = MessageAgent(self.logger)
        # self.queueName = self._messageAgent.genQueueName(SERVER_MANAGER_QUEUE,
        #     self.zoneName)
        # self._messageAgent.startRecvMsg(self.queueName)
        self._messageAgent.startMsgReceiverRPCServer(SERVER_MANAGER_IP, SERVER_MANAGER_PORT)

        self.serverSet = {}
        # self.serverIDMappingTable = {}
        self._timeoutCleaner()
        self._listener()

    def _listener(self):
        while True:
            # msg = self._messageAgent.getMsg(self.queueName)
            msg = self._messageAgent.getMsgByRPC(SERVER_MANAGER_IP, \
                                                    SERVER_MANAGER_PORT)
            # self.logger.debug("msgType:".format(msg.getMessageType()))
            time.sleep(0.1)
            msgType = msg.getMessageType()
            source = msg.getSource()
            if msgType == MSG_TYPE_SERVER_REPLY:
                self._storeServerInfo(msg)
            elif msgType == MSG_TYPE_SERVER_MANAGER_CMD:
                cmd = msg.getbody()
                self._reportServerSet(source, cmd)
            elif msgType == None:
                pass
                # self._printServerSet()
            else:
                self.logger.warning("Unknown msg type {0}".format(msgType))

    def _storeServerInfo(self, msg):
        # type: (SAMMessage) -> None
        server = msg.getbody()  # type: Server
        serverControlNICMac = server.getControlNICMac()
        self.logger.info("Get head beat from server {0}, type: {1}.".format(
            serverControlNICMac, server.getServerType()
        ))
        threadLock.acquire()
        if server.getServerID() == None:
            self.logger.error("Unknown server ID {0}".format(server))
            # if serverControlNICMac in self.serverIDMappingTable.keys():
            #     serverID = self.serverIDMappingTable[serverControlNICMac]
            # else:
            #     serverID = self._assignServerID()
            #     self.serverIDMappingTable[serverControlNICMac] = serverID
            # server.setServerID(serverID)
        serverID = server.getServerID()
        self.serverSet[serverID] = {"server":server, 
            "Active": True, "timestamp":self._getCurrentTime()}
        threadLock.release()

    def _assignServerID(self):
        return len(self.serverSet) + SERVERID_OFFSET

    def _getCurrentTime(self):
        return datetime.datetime.now()

    def _reportServerSet(self, source, cmd):
        # type: (Dict, Command) -> None
        self.logger.info("Get command from mediator.")
        threadLock.acquire()
        cmdRply = self.genGetServersCmdReply(cmd)
        rplyMsg = SAMMessage(MSG_TYPE_SERVER_MANAGER_CMD_REPLY, cmdRply)
        # self._messageAgent.sendMsg(MEDIATOR_QUEUE, msg)
        self._messageAgent.sendMsgByRPC(source["srcIP"],
                                source["srcPort"], rplyMsg)
        threadLock.release()

    def genGetServersCmdReply(self, cmd):
        # type: (Command) -> None
        attributes = {'servers': self.serverSet}
        attributes.update(cmd.attributes)
        cmdRply = CommandReply(cmd.cmdID, CMD_STATE_SUCCESSFUL, attributes)
        return cmdRply

    def _timeoutCleaner(self):
        # start a new thread
        self._timeoutCleanerThread = TimeoutCleaner(self.serverSet,
            self.logger)
        self._timeoutCleanerThread.setDaemon(True)
        self._timeoutCleanerThread.start()

    def _printServerSet(self):
        self.logger.debug("printServerSet:")
        threadLock.acquire()
        for serverKey in self.serverSet.keys():
            self.logger.debug(self.serverSet[serverKey])
            self.logger.debug("----------------------\n")
        self.logger.debug("==============================\n")
        threadLock.release()

    def _async_raise(self, tid, exctype):
        """raises the exception, performs cleanup if needed"""
        tid = ctypes.c_long(tid)
        if not inspect.isclass(exctype):
            exctype = type(exctype)
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid,
                                    ctypes.py_object(exctype))
        if res == 0:
            raise ValueError("Invalid thread id")
        elif res != 1:
            # """if it returns a number greater than one, you're in trouble,
            # and you should call it again with exc=NULL to revert the effect"""
            ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
            raise SystemError("PyThreadState_SetAsyncExc failed")

    def __del__(self):
        # first, delete self._messageAgent or self._timeoutCleanerThread
        # is hard to killed. Still need to address this problem
        thread = self._timeoutCleanerThread
        if version.parse(sys.version.split(' ')[0]) \
                                >= version.parse('3.9'):
            threadLiveness = thread.is_alive()
        else:
            threadLiveness = thread.isAlive()
        if threadLiveness:
            self.logger.warning("Kill thread: %d" %thread.ident)
            self._async_raise(thread.ident, KeyboardInterrupt)
            thread.join()
        del self._messageAgent
        self.logger.info("Delete ServerManager.")


class TimeoutCleaner(threading.Thread):
    def __init__(self, serverSet,
                logger
                ):
        threading.Thread.__init__(self)
        self.serverSet = serverSet
        self.logger = logger
        self.enableServerFailureNotification = SERVER_FAILURE_NOTIFICATION
        self._messageAgent = MessageAgent(self.logger)

    def run(self):
        try:
            self._startTimeout()
        except KeyboardInterrupt:
            self.logger.warning("TimeoutCleaner get KeyboardInterrupt.")
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex)

    def _startTimeout(self):
        if self.enableServerFailureNotification:
            self.logger.info("timeoutCleaner is running")
            while True:
                self.logger.debug("timeoutcleanr run once.")
                threadLock.acquire()
                currentTime = datetime.datetime.now()
                for serverKey in self.serverSet.keys():
                    if (self._getTimeDiff(self.serverSet[serverKey]["timestamp"],
                                currentTime) > SERVER_TIMEOUT
                            and self.serverSet[serverKey]["Active"] == True):
                        self.serverSet[serverKey]["Active"] = False
                        server = self.serverSet[serverKey]["server"]
                        self._sendServerDownTrigger(server)
                threadLock.release()
                time.sleep(TIMEOUT_CLEANER_INTERVAL)

    def _getTimeDiff(self, smallerTime, largerTime):
        difference = largerTime - smallerTime
        seconds_in_day = 24 * 60 * 60
        datetime.timedelta(0, 8, 562000)
        return difference.days * seconds_in_day + difference.seconds

    def _sendServerDownTrigger(self, server):
        # server failure trigger function
        msg = SAMMessage(
            MSG_TYPE_NETWORK_CONTROLLER_CMD,
            Command(
                cmdType = CMD_TYPE_HANDLE_SERVER_STATUS_CHANGE,
                cmdID = uuid.uuid1(),
                attributes = {"serverDown":[server],
                                "serverUp":[]}
            )
        )
        self._messageAgent.sendMsg(NETWORK_CONTROLLER_QUEUE, msg)


if __name__=="__main__":
    argParser = ArgParser()
    zoneName = argParser.getArgs()['zoneName']   # example: None parameter
    severManager = SeverManager(zoneName)
