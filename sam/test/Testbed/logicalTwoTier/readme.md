# start serverAgent on classifier and all nfvis
<!-- ## server2
python ./serverAgent.py 0000:04:00.1  eno2 nfvi 2.2.0.98 -->

To get server information, please read samSimulation/instance/topology.py and find the function addNFVIs4LogicalTwoTier()

## classifier 192.168.0.194
<!-- python ./serverAgent.py  0000:04:00.0 br1 classifier 2.2.0.36 -->
python ./serverAgent.py  0000:04:00.0 eno1 classifier 2.2.0.36

## SFF1 192.168.8.17
python ./serverAgent.py  0000:19:00.1 eno1 nfvi 2.2.0.66

## SFF2 192.168.8.18
python ./serverAgent.py  0000:19:00.1 eno1 nfvi 2.2.0.68

## SFF3 192.168.0.173
python ./serverAgent.py  0000:04:00.0 eno1 nfvi 2.2.0.100

## SFF4 192.168.0.127
python ./serverAgent.py  0000:04:00.0 eno1 nfvi 2.2.0.98

# datapath tester need send arp first!


