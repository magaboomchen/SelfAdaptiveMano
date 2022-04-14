import time

from scapy.all import Raw, sendp, sniff
from scapy.layers.l2 import Ether, ARP
from scapy.layers.inet import IP, TCP

from sam.test.testBase import TESTER_SERVER_DATAPATH_MAC, CLASSIFIER_DATAPATH_IP, \
    WEBSITE_REAL_IP, OUTTER_CLIENT_IP,LB_VNFI1_1_IP
from sam.serverController.vnfController.test.SMPInVM.test_vnfControllerAddSFCI import SFF0_DATAPATH_MAC


def sendDirection1Traffic():
    data = "Hello World"
    ether = Ether(src=TESTER_SERVER_DATAPATH_MAC, dst=SFF0_DATAPATH_MAC)
    ip1 = IP(src=CLASSIFIER_DATAPATH_IP, dst=LB_VNFI1_1_IP)
    ip2 = IP(src=WEBSITE_REAL_IP, dst=OUTTER_CLIENT_IP)
    tcp = TCP(sport=80, dport=1234)
    frame = ether / ip1 / ip2 / tcp /Raw(load=data)
    sendp(frame,iface="ens8")

if __name__=="__main__":
    time.sleep(0.1)
    sendDirection1Traffic()