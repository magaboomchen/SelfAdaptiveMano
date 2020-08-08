import pika
import sys
import base64
import pickle
import time
import uuid
import os
import subprocess
import logging
import Queue
import threading
import datetime
import sys
import ctypes
import inspect

from sam.base.server import Server
from sam.base.messageAgent import *

SERVER_TIMEOUT = 10
TIMEOUT_CLEANER_INTERVAL = 5
SERVERID_OFFSET = 10001

class SeverManager(object):
    def __init__(self):
        logging.info('Init ServerManager')
        self._messageAgent = MessageAgent()
        self._messageAgent.startRecvMsg(SERVER_MANAGER_QUEUE)
        self.serverSet = {}
        self._timeoutCleaner()
        self._listener()

    def _listener(self):
        while True:
            msg = self._messageAgent.getMsg(SERVER_MANAGER_QUEUE)
            logging.debug(msg.getMessageType())
            time.sleep(1)
            if msg.getMessageType() == MSG_TYPE_SERVER_REPLY:
                self._storeServerInfo(msg)
            elif msg.getMessageType() == MSG_TYPE_SERVER_MANAGER_CMD:
                self._reportServerSet()
            elif msg.getMessageType() == None:
                self._printServerSet()
            else:
                logging.warning("Unknown msg type.")

    def _storeServerInfo(self,msg):
        logging.info("Get head beat from server.")
        server = msg.getbody()
        serverControlNICMac = server.getControlNICMac()
        threadLock.acquire()
        if serverControlNICMac in self.serverSet.iterkeys():
            serverID = self.serverSet[serverControlNICMac]["server"].getServerID()
        else:
            serverID = self._assignServerID()
        server.updateServerID(serverID)
        self.serverSet[serverControlNICMac] = {"server":server, "Active": True,"timestamp":self._getCurrentTime()}
        threadLock.release()

    def _assignServerID(self):
        return len(self.serverSet) + SERVERID_OFFSET

    def _getCurrentTime(self):
        return datetime.datetime.now()

    def _reportServerSet(self):
        logging.info("Get request from measurement module.")
        threadLock.acquire()
        self._messageAgent.sendMsg(MEASUREMENT_QUEUE,self.serverSet)
        threadLock.release()

    def _timeoutCleaner(self):
        # start a new thread
        self._timeoutCleanerThread = TimeoutCleaner(self.serverSet)
        self._timeoutCleanerThread.setDaemon(True)
        self._timeoutCleanerThread.start()

    def _printServerSet(self):
        logging.debug("printServerSet:")
        threadLock.acquire()
        for serverKey in self.serverSet.iterkeys():
            logging.debug(self.serverSet[serverKey])
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
        logging.info("Delete ServerManager.")
        thread = self._timeoutCleanerThread
        if thread.isAlive():
            logging.warning("Kill thread: %d" %thread.ident)
            self._async_raise(thread.ident, KeyboardInterrupt)
            thread.join()

class TimeoutCleaner(threading.Thread):
    def __init__(self,serverSet):
        threading.Thread.__init__(self)
        self.serverSet = serverSet

    def run(self):
        try:
            self._startTimeout()
        except KeyboardInterrupt:
            logging.warning("TimeoutCleaner get KeyboardInterrupt.")

    def _startTimeout(self):
        logging.info("timeoutCleaner is running")
        while True:
            logging.debug("timeoutcleanr run once.")
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
    logging.basicConfig(level=logging.INFO)
    severManager = SeverManager()