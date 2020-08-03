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