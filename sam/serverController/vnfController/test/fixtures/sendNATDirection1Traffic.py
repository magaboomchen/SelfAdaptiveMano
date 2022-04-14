import time

from scapy.all import Raw, sendp, sniff
from scapy.layers.l2 import Ether, ARP
from scapy.layers.inet import IP, TCP

from sam.test.testBase import TESTER_SERVER_DATAPATH_MAC, CLASSIFIER_DATAPATH_IP, \
    NAT_VNFI1_1_IP
from sam.serverController.vnfController.test.SMPInVM.test_vnfControllerAddSFCI import SFF0_DATAPATH_MAC


def sendDirection1Traffic():
    data = "Hello World"
    ether = Ether(src=TESTER_SERVER_DATAPATH_MAC, dst=SFF0_DATAPATH_MAC)
    ip1 = IP(src=CLASSIFIER_DATAPATH_IP, dst=NAT_VNFI1_1_IP)
    #ip2 = IP(src=WEBSITE_REAL_IP,dst=NAT_PIP)
    #tcp = UDP(sport=80,dport=NAT_MIN_PORT)
    ip2 = IP(src='5.0.0.5', dst='8.0.8.8')
    tcp = UDP(sport=4969, dport=11111)
    frame = ether / ip1 / ip2 / tcp /Raw(load=data)
    sendp(frame,iface="ens8")

if __name__=="__main__":
    time.sleep(0.1)
    sendDirection1Traffic()