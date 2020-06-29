from scapy.all import *
import logging

BCAST_MAC = 'ff:ff:ff:ff:ff:ff'
class ArpSender():
    def __init__(self, intF, hwAddr, ipAddrList):
        self.intF = intF
        self._hwAddr = hwAddr
        self._ipAddrList = ipAddrList

    def _create_ARP_request_gratuituous(self,ipaddr_to_broadcast):
        arp = ARP(op=2,
                psrc=ipaddr_to_broadcast,
                hwsrc=self._hwAddr,
                pdst=ipaddr_to_broadcast)
        return Ether(src=self._hwAddr, dst=BCAST_MAC) / arp

    def sendGratuitousArp(self):
        logging.warning(self._ipAddrList)
        for ipAddr in self._ipAddrList:
            logging.warning(ipAddr)
            packets = self._create_ARP_request_gratuituous(ipAddr)
            sendp(packets, iface=self.intF, count=1, inter=1)
