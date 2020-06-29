from netifaces import interfaces, ifaddresses, AF_INET
import fcntl
import socket
import struct
import base64
import pickle
import logging
import subprocess

class Server():
    def __init__(self,controlIfName):
        self._serverControlNICMac = self._getHwAddrInKernel(controlIfName)
        self._serverDatapathNICMac = self._getHwAddrInDPDK()
        self._ifSet = {}
        self.updateIfSet()

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
        return self._serverControlNICMac

    def getDatapathNICMac(self):
        return self._serverDatapathNICMac

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
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        info = fcntl.ioctl(s.fileno(), 0x8927,  struct.pack('256s', ifName[:15]))
        return ':'.join(['%02x' % ord(char) for char in info[18:24]])

    def _getIPList(self,ifName):
        addresses = [i['addr'] for i in ifaddresses(ifName).setdefault(AF_INET,[{'addr':'No IP addr'}])  ]
        addList = []
        for add in addresses:
            addList.append( str(add) )
        return addList