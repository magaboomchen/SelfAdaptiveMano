import time

from scapy.all import Raw, sendp
from scapy.layers.l2 import Ether
from scapy.layers.inet import IP, TCP

from sam.test.testBase import TESTER_SERVER_DATAPATH_MAC, CLASSIFIER_DATAPATH_IP, \
    VNFI1_0_IP, WEBSITE_REAL_IP, OUTTER_CLIENT_IP
from sam.serverController.vnfController.test.SMPInVM.test_vnfControllerAddSFCI import SFF0_DATAPATH_MAC


def sendDirection0Traffic():
    data = "Hello World"
    ether = Ether(src=TESTER_SERVER_DATAPATH_MAC, dst=SFF0_DATAPATH_MAC)
    ip1 = IP(src=CLASSIFIER_DATAPATH_IP, dst=VNFI1_0_IP)
    ip2 = IP(src=OUTTER_CLIENT_IP, dst=WEBSITE_REAL_IP)
    tcp = TCP(sport=1234, dport=80)
    frame = ether / ip1 / ip2 / tcp /Raw(load=data)
    sendp(frame,iface="ens8")

if __name__=="__main__":
    time.sleep(0.1)
    sendDirection0Traffic()