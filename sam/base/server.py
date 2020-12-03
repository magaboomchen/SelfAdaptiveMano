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

SERVER_TYPE_CLASSIFIER = "classifier"
SERVER_TYPE_NORMAL = "normal"
SERVER_TYPE_NFVI = "nfvi"
SERVER_TYPE_TESTER = "tester"


class Server(object):
    def __init__(self, controlIfName, datapathIfIP, serverType):
        # each server has at least two nic, one for control, another for data processing
        self._serverID = None
        self._serverType = serverType

        self._controlIfName = controlIfName
        self._serverControlNICMAC = None
        self._serverDatapathNICIP = datapathIfIP
        self._serverDatapathNICMAC = None
        self._ifSet = {}

        self._memoryDesign = None # "SMP", "NUMA"
        self._cpuSocketsNum = None
        self._CPUNum = None # list of int, e.g. [6,6] for two numa nodes
        self._CPUUtil = None # list of float, e.g. [100.0, 0.0, ..., 100.0]
        self._hugepagesTotal = None # list of int, e.g. [14,13] for two numa nodes
        self._hugepagesFree = None # list of int
        self._hugepageSize = None # unit: kB

    def setServerID(self, id):
        self._serverID = id

    def setControlNICIP(self, controlNICIP):
        ifName = self._controlIfName
        self._ifSet[ifName] = {}
        self._ifSet[ifName]["IP"] = controlNICIP

    def setControlNICMAC(self, controlNICMAC):
        self._serverControlNICMAC = controlNICMAC

    def setDataPathNICMAC(self, datapathNICMAC):
        self._serverDatapathNICMAC = datapathNICMAC

    def getServerID(self):
        return self._serverID

    def getServerType(self):
        return self._serverType

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
        if type(self._ifSet[ifName]["IP"]) == list:
            return self._ifSet[ifName]["IP"][0]
        else:
            return self._ifSet[ifName]["IP"]

    def getDatapathNICIP(self):
        if type(self._serverDatapathNICIP) == list:
            return self._serverDatapathNICIP[0]
        else:
            return self._serverDatapathNICIP

    def _getHwAddrInDPDK(self):
        command = "echo -ne \'\n\' | sudo $RTE_SDK/build/app/testpmd | grep \"Port 0: \""
        res = subprocess.Popen(command, shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,close_fds=True)
        result = str(res.stdout.readlines())
        if result.find("Port 0: ")==-1:
            raise ValueError("get data path nic mac address error, maybe run out of hugepages?")
        final = result.split(' ')[2][0:17]
        return final

    def _getHwAddrInKernel(self, ifName):
        ethMac = get_mac_address(interface=ifName)
        return ethMac

    def _getIPList(self, ifName):
        addresses = [i['addr'] for i in ifaddresses(ifName).setdefault(AF_INET,[{'addr':'No IP addr'}])  ]
        addList = []
        for add in addresses:
            addList.append( str(add) )
        return addList

    def printCpuUtil(self):
        for x in range(10):
            logging.info(psutil.cpu_percent(interval=1, percpu=True))

    def updateResource(self):
        self._updateMemDesign()
        self._updateSocketsNum()
        self._updateCpuCount()
        self._updateCpuUtil()
        self._updateHugepagesTotal()
        self._updateHugepagesFree()
        self._updateHugepagesSize()

    def _updateMemDesign(self):
        rv = subprocess.check_output("lscpu | grep -i numa | grep 'NUMA node(s):'", shell=True)
        rv = int(rv.strip("\n").split(":")[1])
        if rv <= 1:
            self._memoryDesign = "SMP"
        else:
            self._memoryDesign = "NUMA"

    def _updateSocketsNum(self):
        self._cpuSocketsNum =  int(subprocess.check_output('cat /proc/cpuinfo | grep "physical id" | sort -u | wc -l', shell=True))

    def _updateCpuCount(self):
        self._CPUNum = []
        for nodeIndex in range(self._cpuSocketsNum):
            regexp = "'NUMA node{0} CPU(s):'".format(nodeIndex)
            cmd = "lscpu | grep -i numa | grep {0}".format(regexp)
            print(cmd)
            rv = subprocess.check_output([cmd], shell=True)
            rv = rv.strip("\n").split(":")[1].split(",")
            coreNum = len(rv)
            self._CPUNum.append(coreNum)

    def _updateCpuUtil(self):
        self._CPUUtil = psutil.cpu_percent(percpu=True)

    def _updateHugepagesTotal(self):
        self._hugepagesTotal = []
        for nodeIndex in range(self._cpuSocketsNum):
            regexp = "'Node {0} HugePages_Total:'".format(nodeIndex)
            cmd = "cat /sys/devices/system/node/node*/meminfo | fgrep Huge | grep {0}".format(regexp)
            print(cmd)
            rv = subprocess.check_output([cmd], shell=True)
            rv = int(rv.strip("\n").split(":")[1])
            self._hugepagesTotal.append(rv)

    def _updateHugepagesFree(self):
        self._hugepagesFree = []
        for nodeIndex in range(self._cpuSocketsNum):
            regexp = "'Node {0} HugePages_Free:'".format(nodeIndex)
            cmd = "cat /sys/devices/system/node/node*/meminfo | fgrep Huge | grep {0}".format(regexp)
            print(cmd)
            rv = subprocess.check_output([cmd], shell=True)
            rv = int(rv.strip("\n").split(":")[1])
            self._hugepagesFree.append(rv)

    def _updateHugepagesSize(self):
        out_bytes = subprocess.check_output(['grep Huge /proc/meminfo | grep Hugepagesize'], shell=True)
        self._hugepageSize = int(out_bytes.split(':')[1].split('kB')[0])

    def __str__(self):
        string = "{0}\n".format(self.__class__)
        for key,values in self.__dict__.items():
            string = string + "{0}:{1}\n".format(key, values)
        return string

    def __repr__(self):
        return str(self)
