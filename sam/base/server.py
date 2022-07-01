#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging
import subprocess

import psutil
from netifaces import interfaces, ifaddresses, AF_INET
from getmac import get_mac_address

SERVER_TYPE_CLASSIFIER = "classifier"
SERVER_TYPE_NORMAL = "normal"
SERVER_TYPE_NFVI = "nfvi"
SERVER_TYPE_TESTER = "tester"


class Server(object):
    def __init__(self, controlIfName, datapathIfIP, serverType):
        # each server has at least two nic, one for control, another for data processing
        self._serverID = None  # an uuid
        self._serverType = serverType

        self._controlIfName = controlIfName  # string, e.g. "eno2"
        self._serverControlNICIP = None  # string, e.g. "2.2.0.35"
        self._serverControlNICMAC = None  # string, e.g. "18:66:da:86:4c:16"
        self._serverDatapathNICIP = datapathIfIP  # string, e.g. "2.2.0.36"
        self._serverDatapathNICMAC = None  # string, e.g. "18:66:da:86:4c:16"
        self._ifSet = {}  # self.updateIfSet()

        self._routingTag = {}  # 4 type routing tag
        # ['ip'] = ['ip1', 'ip2']
        # ['identification'] = ['id1', 'id2']
        # ['geo'] = ['geo1', 'geo2']
        # ['content'] = ['c1', 'c2']

        self._supportVNFSet = []  # see vnf.py, e.g. [VNF_TYPE_FW, VNF_TYPE_IDS]

        self._memoryAccessMode = None  # "SMP", "NUMA"
        # There is a misunderstanding between socket and NUMA, we need discuss with DPDK community
        self._socketNum = None  # int
        self._coreSocketDistribution = None  # list of int, e.g. [6,6] means socket 0 has 6 cores, socket 1 has 6 cores
        self._numaNum = None  # int
        self._coreNUMADistribution = None  # list of list, e.g. [[0,2,4,6,8,10],[1,3,5,7,9,11]]
        self._coreUtilization = None  # list of float, e.g. [100.0, 0.0, ..., 100.0]
        self._hugepagesTotal = None  # list of int, e.g. [14,13] for two numa nodes
        self._hugepagesFree = None  # list of int, e.g. [10,13] for two numa nodes
        self._hugepageSize = None  # unit: kB
        self._nicBandwidth = 10  # unit: Gbps, default is 10 Gbps

    def setServerID(self, serverID):
        self._serverID = serverID

    def setControlNICIP(self, controlNICIP):
        self._serverControlNICIP = controlNICIP

        ifName = self._controlIfName
        self._ifSet[ifName] = {}
        self._ifSet[ifName]["IP"] = controlNICIP

    def setControlNICMAC(self, controlNICMAC):
        self._serverControlNICMAC = controlNICMAC.lower()

    def setDataPathNICMAC(self, datapathNICMAC):
        self._serverDatapathNICMAC = datapathNICMAC.lower()

    def getServerID(self):
        return self._serverID

    def getServerType(self):
        return self._serverType

    def updateControlNICMAC(self):
        self._serverControlNICMAC \
            = self._getHwAddrInKernel(self._controlIfName).lower()

    def updateDataPathNICMAC(self):
        self._serverDatapathNICMAC = self._getHwAddrInDPDK().lower()

    def updateIfSet(self):
        # update all interface information controlled by linux kernel
        for intf in interfaces():
            ifName = str(intf)
            self._ifSet[ifName] = {}
            # get mac address
            mac = self._getHwAddrInKernel(ifName)
            self._ifSet[ifName]["MAC"] = mac.lower()
            # get ip addresses
            ipList = self._getIPList(ifName)
            self._ifSet[ifName]["IP"] = ipList

    def getIfSet(self):
        return self._ifSet

    def printIfSet(self):
        for key, value in self._ifSet.items():
            logging.info('{key}:{value}'.format(key=key, value=value))

    def getControlNICMac(self):
        return self._serverControlNICMAC.lower()

    def getDatapathNICMac(self):
        return self._serverDatapathNICMAC.lower()

    # def getServerControlNICIP(self):
    #     return self._serverControlNICIP

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
        res = subprocess.Popen(command, shell=True,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
        result = res.stdout.readlines()
        outputText = str(result)
        if outputText.find("Port 0: ") == -1:
            raise ValueError("get data path nic mac address error, maybe run out of hugepages?")

        for reg in result:
            if reg.count(":") == 6:
                final = reg.split(' ')[2][0:17]
                break
            elif reg.find("Link Down") != -1:
                print("link down")
                # raise ValueError("datapath nic link down!")
        else:
            raise ValueError("get data path nic mac address error, unknown reason.")
        return final

    def _getHwAddrInKernel(self, ifName):
        ethMac = get_mac_address(interface=ifName)
        return ethMac.lower()

    def _getIPList(self, ifName):
        addresses = [i['addr'] for i in ifaddresses(ifName).setdefault(AF_INET, [{'addr': 'No IP addr'}])]
        addList = []
        for add in addresses:
            addList.append(str(add))
        return addList

    def addVNFSupport(self, vnfType):
        self._supportVNFSet.append(vnfType)

    def getVNFSupport(self):
        return self._supportVNFSet

    def isSupportVNF(self, vnfType):
        return vnfType in self._supportVNFSet

    def printCpuUtil(self):
        for x in range(10):
            logging.info(psutil.cpu_percent(interval=1, percpu=True))

    def getMemoryAccessMode(self):
        return self._memoryAccessMode

    def getSocketNum(self):
        return self._socketNum

    def getCoreSocketDistribution(self):
        return self._coreSocketDistribution

    def getNUMANum(self):
        return self._numaNum

    def getCoreNUMADistribution(self):
        return self._coreNUMADistribution

    def setCoreNUMADistribution(self, coreNUMADistribution):
        self._coreNUMADistribution = coreNUMADistribution

    def getCpuUtil(self):
        return self._coreUtilization

    def setHugepagesTotal(self, hugepagesTotal):
        self._hugepagesTotal = hugepagesTotal

    def getHugepagesTotal(self):
        return self._hugepagesTotal

    def getHugepagesFree(self):
        return self._hugepagesFree

    def getHugepagesSize(self):
        return self._hugepageSize

    def getMaxCores(self):
        coreNum = 0
        for item in self.getCoreNUMADistribution():
            coreNum = coreNum + len(item)
        return coreNum - 2  # reserve one core for OS and one core for BESS

    def getMaxMemory(self):
        hugepages = 0
        for pages in self.getHugepagesTotal():
            hugepages = hugepages + pages
        return hugepages * self.getHugepagesSize() / 1024 / 1024  # unit: GB

    def fastConstructResourceInfo(self):
        # For fast server instance construction
        self._memoryAccessMode = "NUMA"
        self._socketNum = 2
        self._coreSocketDistribution = [12, 12]
        self._numaNum = 2
        self._coreNUMADistribution = [12, 12]
        self._coreUtilization = [0] * 24
        self._hugepagesTotal = [256, 256]
        self._hugepagesFree = [256, 256]
        self._hugepageSize = 1048576

    def updateResource(self):
        self._updateMemAccessMode()
        self._updateSocketNum()
        self._updateCoreSocketDistribution()
        self._updateNUMANum()
        self._updateCoreNUMADistribution()
        self._updateCpuUtil()
        self._updateHugepagesTotal()
        self._updateHugepagesFree()
        self._updateHugepagesSize()

    def __isSMP(self):
        rv = subprocess.check_output("lscpu | grep -i 'Socket(s)'", shell=True)
        rv = str(rv)
        rv = int(rv.split(":")[1].strip("\\n'"))
        return rv == 1

    def _updateMemAccessMode(self):
        if self.__isSMP():
            self._memoryAccessMode = "SMP"
            return None
        rv = subprocess.check_output("lscpu | grep -i numa | grep 'NUMA node(s):'", shell=True)
        rv = int(rv.strip("\n").split(":")[1])
        if rv <= 1:
            self._memoryAccessMode = "SMP"
        else:
            self._memoryAccessMode = "NUMA"

    def _updateSocketNum(self):
        rv = subprocess.check_output(' lscpu | grep Socket ', shell=True)
        rv = str(rv)
        rv = int(rv.split(":")[1].strip("\\n'"))
        self._socketNum = int(rv)

    def _getSMPCoresNum(self):
        rv = subprocess.check_output(" lscpu | grep 'CPU(s):' ", shell=True)
        rv = str(rv)
        rv = int(rv.split(":")[1].strip("\\n'"))
        return rv

    def _updateCoreSocketDistribution(self):
        self._coreSocketDistribution = []
        if self.__isSMP():
            self._coreSocketDistribution = [list(range(self._getSMPCoresNum()))]
            return None
        for nodeIndex in range(self._socketNum):
            regexp = "'NUMA node{0} CPU(s):'".format(nodeIndex)
            cmd = "lscpu | grep -i numa | grep {0}".format(regexp)
            rv = subprocess.check_output([cmd], shell=True)
            rv = str(rv)
            rv = rv.strip("\n").split(":")[1].split(",")
            coreNum = len(rv)
            self._coreSocketDistribution.append(coreNum)

    def _updateNUMANum(self):
        if self.__isSMP():
            self._numaNum = 1
            return None
        rv = subprocess.check_output(" lscpu | grep 'NUMA node(s)' ", shell=True)
        rv = str(rv)
        rv = rv.strip("\n").split(":")[1]
        self._numaNum = int(rv)

    def _updateCoreNUMADistribution(self):
        self._coreNUMADistribution = []
        if self.__isSMP():
            self._coreNUMADistribution = [list(range(self._getSMPCoresNum()))]
            return None
        for nodeIndex in range(self._socketNum):
            regexp = "'NUMA node{0} CPU(s):'".format(nodeIndex)
            cmd = "lscpu | grep -i numa | grep {0}".format(regexp)
            rv = subprocess.check_output([cmd], shell=True)
            rv = str(rv)
            rv = rv.strip("\n").split(":")[1]
            if rv.find(",") != -1:
                rv = rv.split(",")
                rv = map(lambda x: int(x), rv)
            elif rv.find("-") != -1:
                rv = rv.split("-")
                rv = map(lambda x: int(x), rv)
                rv = range(rv[0], rv[1] + 1)
            else:
                raise ValueError("Can't parse NUMA Core")
            self._coreNUMADistribution.append(rv)

    def _updateCpuUtil(self):
        self._coreUtilization = psutil.cpu_percent(percpu=True)

    def _updateHugepagesTotal(self):
        self._hugepagesTotal = []
        if self.__isSMP():
            return None
        for nodeIndex in range(self._socketNum):
            regexp = "'Node {0} HugePages_Total:'".format(nodeIndex)
            cmd = "cat /sys/devices/system/node/node*/meminfo | fgrep Huge | grep {0}".format(regexp)
            rv = subprocess.check_output([cmd], shell=True)
            rv = str(rv)
            rv = int(rv.strip("\n").split(":")[1])
            self._hugepagesTotal.append(rv)

    def _updateHugepagesFree(self):
        self._hugepagesFree = []
        if self.__isSMP():
            rv = subprocess.check_output(" grep Huge /proc/meminfo | grep 'HugePages_Free:' ", shell=True)
            rv = str(rv)
            rv = int(rv.split(":")[1].strip("\\n'"))
            self._hugepagesFree.append(rv)
            return None
        for nodeIndex in range(self._socketNum):
            regexp = "'Node {0} HugePages_Free:'".format(nodeIndex)
            cmd = "cat /sys/devices/system/node/node*/meminfo | fgrep Huge | grep {0}".format(regexp)
            rv = subprocess.check_output([cmd], shell=True)
            rv = str(rv)
            rv = int(rv.strip("\n").split(":")[1])
            self._hugepagesFree.append(rv)

    def _updateHugepagesSize(self):
        out_bytes = subprocess.check_output(['grep Huge /proc/meminfo | grep Hugepagesize'], shell=True)
        out_bytes = str(out_bytes)
        self._hugepageSize = int(out_bytes.split(':')[1].split('kB')[0])

    def setNICBandwidth(self, bandwidth):
        self._nicBandwidth = bandwidth

    def getNICBandwidth(self):
        return self._nicBandwidth

    def setCpuUtil(self, util):
        self._coreUtilization = util

    def setHugePages(self, pages):
        self._hugepagesFree = pages

    def __str__(self):
        string = "{0}\n".format(self.__class__)
        for key, values in self.__dict__.items():
            string = string + "{0}:{1}\n".format(key, values)
        return string

    def __repr__(self):
        return str(self)

# if __name__ =="__main__":
#     _NUMACpuCore = []
#     for nodeIndex in range(2):
#         regexp = "'NUMA node{0} CPU(s):'".format(nodeIndex)
#         cmd = "lscpu | grep -i numa | grep {0}".format(regexp)
#         rv = subprocess.check_output([cmd], shell=True)
#         rv = rv.strip("\n").split(":")[1]
#         if rv.find(",") != -1:
#             rv = rv.split(",")
#             rv = map(lambda x : int(x), rv) 
#         elif rv.find("-") != -1:
#             rv = rv.split("-")
#             rv = map(lambda x : int(x), rv) 
#             rv = range(rv[0], rv[1]+1)
#         else:
#             raise ValueError("Can't parse NUMA Core")
#         _NUMACpuCore.append(rv)

#     rv = subprocess.check_output(' lscpu | grep Socket ', shell=True)
#     rv = rv.strip("\n").split(":")[1]
#     print(int(rv))

#     rv = subprocess.check_output(" lscpu | grep 'NUMA node(s)' ", shell=True)
#     rv = rv.strip("\n").split(":")[1]
#     print(int(rv))

#     reg = 'Port 0: 00:1B:21:C0:8F:98\n'
#     print(reg.count(":") == 6)
