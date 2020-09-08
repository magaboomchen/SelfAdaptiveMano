#!/usr/bin/python
# -*- coding: UTF-8 -*-

import fcntl
import socket
import struct
import base64
import logging
import subprocess
import sys

import psutil
import pickle
from netifaces import interfaces, ifaddresses, AF_INET
from getmac import get_mac_address


SERVER_TYPE_CLASSIFIER = "SERVER_TYPE_CLASSIFIER"
SERVER_TYPE_NORMAL = "SERVER_TYPE_NORMAL"
SERVER_TYPE_TESTER = "SERVER_TYPE_TESTER"

class Server(object):
    def __init__(self,controlIfName, datapathIfIP, serverType):
        # each server has at least two nic, one for control, another for data processing
        self._serverID = None
        self._serverType = serverType

        self._controlIfName = controlIfName
        self._serverControlNICMAC = None
        self._serverDatapathNICIP = datapathIfIP
        self._serverDatapathNICMAC = None
        self._ifSet = {}

        self._CPUNum = None
        self._CPUUtil = None
        self._hugepagesTotal = None
        self._hugepagesFree = None
        self._hugepageSize = None

    def setServerID(self, id):
        self._serverID = id

    def setControlNICIP(self,controlNICIP):
        ifName = self._controlIfName
        self._ifSet[ifName] = {}
        self._ifSet[ifName]["IP"] = controlNICIP

    def setControlNICMAC(self,controlNICMAC):
        self._serverControlNICMAC = controlNICMAC

    def setDataPathNICMAC(self,datapathNICMAC):
        self._serverDatapathNICMAC = datapathNICMAC

    def getServerID(self):
        return self._serverID

    def updateControlNICMAC(self):
        self._serverControlNICMAC = self._getHwAddrInKernel(self._controlIfName)

    def updateDataPathNICMAC(self):
        self._serverDatapathNICMAC = self._getHwAddrInDPDK()

    def updateIfSet(self):
        # update all interface information controlled by linux kernel
        for intf in interfaces():
            ifName = str(intf)
            self._ifSet[ifName] = {}
            # get mac address
            mac = self._getHwAddrInKernel(ifName)
            self._ifSet[ifName]["MAC"] = mac
            # get ip addresses
            ipList = self._getIPList(ifName)
            self._ifSet[ifName]["IP"] = ipList

    def getIfSet(self):
        return self._ifSet

    def printIfSet(self):
        for key,value in self._ifSet.items():
            logging.info('{key}:{value}'.format(key = key, value = value))

    def getControlNICMac(self):
        return self._serverControlNICMAC

    def getDatapathNICMac(self):
        return self._serverDatapathNICMAC

    def getControlNICIP(self):
        ifName = self._controlIfName
        return self._ifSet[ifName]["IP"]

    def getDatapathNICIP(self):
        return self._serverDatapathNICIP

    def _getHwAddrInDPDK(self):
        command = "echo -ne \'\n\' | sudo $RTE_SDK/x86_64-native-linuxapp-gcc/app/testpmd | grep \"Port 0: \""
        res = subprocess.Popen(command, shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,close_fds=True)
        result = str(res.stdout.readlines())
        if result.find("Port 0: ")==-1:
            logging.error("get data path nic mac address error, maybe run out of hugepages?")
            exit(1)
        final = result.split(' ')[2][0:17]
        return final

    def _getHwAddrInKernel(self,ifName):
        # s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # info = fcntl.ioctl(s.fileno(), 0x8927,  struct.pack('256s', ifName[:15]))
        # return ':'.join(['%02x' % ord(char) for char in info[18:24]])
        ethMac = get_mac_address(interface=ifName)
        return ethMac

    def _getIPList(self,ifName):
        addresses = [i['addr'] for i in ifaddresses(ifName).setdefault(AF_INET,[{'addr':'No IP addr'}])  ]
        addList = []
        for add in addresses:
            addList.append( str(add) )
        return addList

    def printCpuUtil(self):
        for x in range(10):
            print(psutil.cpu_percent(interval=1, percpu=True))

    def updateResource(self):
        self._updateCpuCount()
        self._updateCpuUtil()
        self._updateHugepagesTotal()
        self._updateHugepagesFree()
        self._updateHugepagesSize()

    def _updateCpuCount(self):
        self._CPUNum = len(psutil.cpu_percent(percpu=True))

    def _updateCpuUtil(self):
        self._CPUUtil = sum(psutil.cpu_percent(percpu=True))/len(psutil.cpu_percent(percpu=True))

    def _updateHugepagesTotal(self):
        out_bytes = subprocess.check_output(['grep Huge /proc/meminfo | grep HugePages_Total'], shell=True)
        self._hugepagesTotal = int(out_bytes.split(':')[1])

    def _updateHugepagesFree(self):
        out_bytes = subprocess.check_output(['grep Huge /proc/meminfo | grep HugePages_Free'], shell=True)
        self._hugepagesFree = int(out_bytes.split(':')[1])

    def _updateHugepagesSize(self):
        out_bytes = subprocess.check_output(['grep Huge /proc/meminfo | grep Hugepagesize'], shell=True)
        self._hugepageSize = int(out_bytes.split(':')[1].split('kB')[0])