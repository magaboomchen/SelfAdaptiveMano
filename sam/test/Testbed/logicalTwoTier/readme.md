# start serverAgent on classifier and all nfvis
## server2
python ./serverAgent.py 0000:04:00.1  eno2 nfvi 2.2.0.98

## classifier 192.168.0.194
python ./serverAgent.py  0000:04:00.0 br1 classifier 2.2.0.36




# datapath tester need send arp first!


