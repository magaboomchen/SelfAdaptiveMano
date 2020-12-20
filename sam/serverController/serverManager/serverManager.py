#!/usr/bin/python
# -*- coding: UTF-8 -*-

import sys
import time
import threading
import ctypes
import inspect

import datetime

from sam.base.server import Server
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.messageAgent import *
from sam.base.command import *
from sam.serverController.serverManager.argParser import ArgParser

SERVER_TIMEOUT = 10
TIMEOUT_CLEANER_INTERVAL = 5
SERVERID_OFFSET = 10001


class SeverManager(object):
    def __init__(self, zoneName=""):
        logConfigur = LoggerConfigurator(__name__, './log',
            'serverManager.log', level='debug')
        self.logger = logConfigur.getLogger()
        self.logger.info('Init ServerManager')

        self._messageAgent = MessageAgent(self.logger)
        self.queueName = self._messageAgent.genQueueName(SERVER_MANAGER_QUEUE,
            zoneName)
        self._messageAgent.startRecvMsg(self.queueName)

        self.serverSet = {}
        self.serverIDMappingTable = {}
        self._timeoutCleaner()
        self._listener()

    def _listener(self):
        while True:
            msg = self._messageAgent.getMsg(self.queueName)
            self.logger.debug("msgType:".format(msg.getMessageType()))
            time.sleep(1)
            if msg.getMessageType() == MSG_TYPE_SERVER_REPLY:
                self._storeServerInfo(msg)
            elif msg.getMessageType() == MSG_TYPE_SERVER_MANAGER_CMD:
                cmd = msg.getbody()
                self._reportServerSet(cmd)
            elif msg.getMessageType() == None:
                self._printServerSet()
            else:
                self.logger.warning("Unknown msg type.")

    def _storeServerInfo(self,msg):
        server = msg.getbody()
        serverControlNICMac = server.getControlNICMac()
        self.logger.info("Get head beat from server {0}, type: {1}.".format(
            serverControlNICMac, server.getServerType()
        ))
        threadLock.acquire()
        if serverControlNICMac in self.serverIDMappingTable.iterkeys():
            serverID = self.serverIDMappingTable[serverControlNICMac]
        else:
            serverID = self._assignServerID()
            self.serverIDMappingTable[serverControlNICMac] = serverID
        # if serverControlNICMac in self.serverSet.iterkeys():
        #     serverID = self.serverSet[serverControlNICMac]["server"].getServerID()
        # else:
        #     serverID = self._assignServerID()
        server.setServerID(serverID)
        self.serverSet[serverID] = {"server":server, 
            "Active": True, "timestamp":self._getCurrentTime()}
        threadLock.release()

    def _assignServerID(self):
        return len(self.serverSet) + SERVERID_OFFSET

    def _getCurrentTime(self):
        return datetime.datetime.now()

    def _reportServerSet(self, cmd):
        self.logger.info("Get command from mediator.")
        threadLock.acquire()
        cmdRply = self.genGetServersCmdReply(cmd)
        msg = SAMMessage(MSG_TYPE_SERVER_MANAGER_CMD_REPLY, cmdRply)
        self._messageAgent.sendMsg(MEDIATOR_QUEUE, msg)
        threadLock.release()

    def genGetServersCmdReply(self, cmd):
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
        for serverKey in self.serverSet.iterkeys():
            self.logger.debug(self.serverSet[serverKey])
            self.logger.debug("----------------------\n")
        self.logger.debug("==============================\n")
        threadLock.release()

    def _async_raise(self,tid, exctype):
        """raises the exception, performs cleanup if needed"""
        tid = ctypes.c_long(tid)
        if not inspect.isclass(exctype):
            exctype = type(exctype)
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(exctype))
        if res == 0:
            raise ValueError("Invalid thread id")
        elif res != 1:
            # """if it returns a number greater than one, you're in trouble,
            # and you should call it again with exc=NULL to revert the effect"""
            ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
            raise SystemError("PyThreadState_SetAsyncExc failed")

    def __del__(self):
        # first, delet self._messageAgent, or self._timeoutCleanerThread is hard to killed. Still need to address this problem
        del self._messageAgent
        self.logger.info("Delete ServerManager.")
        thread = self._timeoutCleanerThread
        if thread.isAlive():
            self.logger.warning("Kill thread: %d" %thread.ident)
            self._async_raise(thread.ident, KeyboardInterrupt)
            thread.join()


class TimeoutCleaner(threading.Thread):
    def __init__(self, serverSet, logger):
        threading.Thread.__init__(self)
        self.serverSet = serverSet
        self.logger = logger

    def run(self):
        try:
            self._startTimeout()
        except KeyboardInterrupt:
            self.logger.warning("TimeoutCleaner get KeyboardInterrupt.")

    def _startTimeout(self):
        self.logger.info("timeoutCleaner is running")
        while True:
            self.logger.debug("timeoutcleanr run once.")
            threadLock.acquire()
            currentTime = datetime.datetime.now()
            for serverKey in self.serverSet.iterkeys():
                if self._getTimeDiff(self.serverSet[serverKey]["timestamp"], currentTime) > SERVER_TIMEOUT:
                    self.serverSet[serverKey]["Active"] = False
            threadLock.release()
            time.sleep(TIMEOUT_CLEANER_INTERVAL)

    def _getTimeDiff(self, smallerTime, largerTime):
        difference = largerTime - smallerTime
        seconds_in_day = 24 * 60 * 60
        datetime.timedelta(0, 8, 562000)
        return difference.days * seconds_in_day + difference.seconds


if __name__=="__main__":
    argParser = ArgParser()
    zoneName = argParser.getArgs()['zoneName']   # example: None parameter
    severManager = SeverManager(zoneName)
