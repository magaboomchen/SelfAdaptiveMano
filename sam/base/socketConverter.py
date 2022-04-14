#!/usr/bin/python
# -*- coding: UTF-8 -*-

import socket
import struct

ETHERTYPE_IP = 0x0800
ETHERTYPE_ARP = 0x0806
BCAST_MAC = 'ff:ff:ff:ff:ff:ff'


class SocketConverter(object):
    def __init__(self):
        pass

    def aton(self,ip):
        return socket.inet_aton(ip)

    def ntohl(self,num):
        return socket.ntohl(num)

    def htonl(self,num):
        return socket.htonl(num)

    def htons(self,num):
        return socket.htons(num)
    
    def ntohs(self,num):
        return socket.ntohs(num)

    def ip2int(self,addr):
        return struct.unpack("!I", socket.inet_aton(addr))[0]

    def int2ip(self,addr):
        return socket.inet_ntoa(struct.pack("!I", addr))

    def ipPrefix2Mask(self,ipPrefix):
        num = (0xFFFFFFFF00000000 >> ipPrefix) & 0XFFFFFFFF
        return self.int2ip(int(num))

    def bytes2Int(self,bYtes):
        result = 0
        for b in list(bYtes):
            b = ord(b)
            result = result * 256 + int(b)
        return result

    def int2Bytes(self, value, bytesLength):
        result = []
        for i in range(0, bytesLength):
            result.append(value >> (i * 8) & 0xff)
        result.reverse()
        result = bytes(bytearray(result))
        return result

    # def int2BytesPython27(self, num):
    #     # bugs: can't assign bytes length
    #     num = hex(num).replace('0x','')
    #     if len(num)%2 == 1:
    #         num = '0' + num
    #     return num.decode("hex")

    def getFullMaskInHex(self, identifierBits):
        fullMask = 0x0
        for i in range(identifierBits):
            fullMask = fullMask + ( 0x1 << i )
        return hex(fullMask)

    def isInSameLAN(self, IP1, IP2, prefixNum):
        IPNum1 = self.ip2int(IP1)
        IPNum2 = self.ip2int(IP2)
        netIPMask = self.ipPrefix2Mask(prefixNum)
        netIPMaskNum = self.ip2int(netIPMask)
        return (IPNum1 & netIPMaskNum) == (IPNum2 & netIPMaskNum)

    def isLANIP(self, dstIP, net):
        dstIPNum = self.ip2int(dstIP)

        netIP = net.split('/')[0]        
        netIPNum = self.ip2int(netIP)

        netIPPrefixNum = int(net.split('/')[1])
        netIPMask = self.ipPrefix2Mask(netIPPrefixNum)
        netIPMaskNum = self.ip2int(netIPMask)

        return (dstIPNum & netIPMaskNum) == (netIPNum & netIPMaskNum)
