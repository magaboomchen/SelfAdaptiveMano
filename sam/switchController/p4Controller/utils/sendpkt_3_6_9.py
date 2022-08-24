from scapy.all import *
from scapy.contrib.nsh import *

#icmppkt = Ether(src = '20:22:33:44:55:66', dst = '20:22:33:44:55:77')
#icmppkt = icmppkt / IP(src = '10.10.10.12', dst = '192.168.100.4', ttl = 64) 
#icmppkt = icmppkt / ICMP(id = 8) / B'99090909999909'

#sendp(icmppkt, iface = 'enp5s0f1')

nshpkt = Ether(src = '20:22:33:44:55:66', dst = '20:22:33:44:55:77')
nshpkt = nshpkt / NSH(spi = 1, si = 1)
nshpkt = nshpkt / IP(src = '10.10.10.12', dst = '192.168.100.4', ttl = 64) / B'abcdefghijklmn'

wrpcap('tmp.pcap', nshpkt)
sendp(nshpkt, iface = 'ens10np1')

# /home/yyl/miniconda3/envs/bessenv/bin/python3
