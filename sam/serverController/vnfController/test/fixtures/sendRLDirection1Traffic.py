import time

from scapy.all import Raw, sendp, sniff
from scapy.layers.l2 import Ether, ARP
from scapy.layers.inet import IP, TCP
from scapy.contrib.nsh import NSH

from sam.test.testBase import RL_VNFI1_1_IP, TESTER_SERVER_DATAPATH_MAC, CLASSIFIER_DATAPATH_IP, \
    WEBSITE_REAL_IP, OUTTER_CLIENT_IP, SFF1_DATAPATH_MAC, \
    DIRECTION1_TRAFFIC_SI, DIRECTION1_TRAFFIC_SPI
from sam.serverController.sffController.test.component.testConfig import TESTER_DATAPATH_INTF, \
    TESTER_SERVER_DATAPATH_MAC
from sam.serverController.sffController.sfcConfig import CHAIN_TYPE_NSHOVERETH, CHAIN_TYPE_UFRR, \
    DEFAULT_CHAIN_TYPE


def sendDirection1Traffic():
    data = "Hello World"
    ether = Ether(src=TESTER_SERVER_DATAPATH_MAC, dst=SFF1_DATAPATH_MAC)
    ip2 = IP(src=WEBSITE_REAL_IP, dst=OUTTER_CLIENT_IP)
    tcp = TCP(sport=80, dport=1234)
    if DEFAULT_CHAIN_TYPE == CHAIN_TYPE_UFRR:
        ip1 = IP(src=CLASSIFIER_DATAPATH_IP, dst=RL_VNFI1_1_IP)
        frame = ether / ip1 / ip2 / tcp / Raw(load=data)
    elif DEFAULT_CHAIN_TYPE == CHAIN_TYPE_NSHOVERETH:
        nsh = NSH(spi = DIRECTION1_TRAFFIC_SPI, si = DIRECTION1_TRAFFIC_SI, nextproto=0x1, length=0x6)
        frame = ether / nsh / ip2 / tcp / Raw(load=data)
    sendp(frame,iface=TESTER_DATAPATH_INTF)
    frame.show()

if __name__=="__main__":
    time.sleep(0.1)
    sendDirection1Traffic()