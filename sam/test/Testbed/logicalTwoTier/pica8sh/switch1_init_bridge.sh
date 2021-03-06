#!/bin/sh
# encoding: utf-8.0

echo "delete bridge"
ovs-vsctl del-br br0
ovs-vsctl del-br br1
ovs-vsctl del-br br2
ovs-vsctl del-br br3
ovs-vsctl del-br br4
ovs-vsctl del-br br5
ovs-vsctl del-br br6
ovs-vsctl del-br br7

echo "add bridge"
ovs-vsctl add-br br1 -- set bridge br1 datapath_type=pica8 protocols=OpenFlow13
ovs-vsctl add-br br5 -- set bridge br5 datapath_type=pica8 protocols=OpenFlow13
ovs-vsctl add-br br6 -- set bridge br6 datapath_type=pica8 protocols=OpenFlow13
ovs-vsctl add-br br7 -- set bridge br7 datapath_type=pica8 protocols=OpenFlow13

echo "set bridge"
ovs-vsctl set bridge br1 other_config:datapath-id=0000000000000001
ovs-vsctl set bridge br5 other_config:datapath-id=0000000000000005
ovs-vsctl set bridge br6 other_config:datapath-id=0000000000000006
ovs-vsctl set bridge br7 other_config:datapath-id=0000000000000007

ovs-vsctl set bridge br1 other_config:disable-in-band=true
ovs-vsctl set bridge br5 other_config:disable-in-band=true
ovs-vsctl set bridge br6 other_config:disable-in-band=true
ovs-vsctl set bridge br7 other_config:disable-in-band=true

# define addPort function
addPort()
{
    echo "add interface" $2 "to bridge" $1
    ovs-vsctl add-port $1 $2 vlan_mode=trunk tag=1 -- set interface $2 type=pica8
}

addPort br1 ge-1/1/26
addPort br1 ge-1/1/28
addPort br1 ge-1/1/30
addPort br1 te-1/1/49
addPort br1 te-1/1/52

addPort br5 ge-1/1/32
addPort br5 ge-1/1/34
addPort br5 ge-1/1/36

addPort br6 ge-1/1/38
addPort br6 ge-1/1/40
addPort br6 ge-1/1/42

addPort br7 ge-1/1/48
addPort br7 te-1/1/50
addPort br7 te-1/1/51

echo "del-flows"
ovs-ofctl del-flows br1
ovs-ofctl del-flows br5
ovs-ofctl del-flows br6
ovs-ofctl del-flows br7

echo "set controller"
ovs-vsctl set-controller br1 tcp:192.168.0.194:6633
ovs-vsctl set-controller br5 tcp:192.168.0.194:6633
ovs-vsctl set-controller br6 tcp:192.168.0.194:6633

echo "add flow for Inbound traffic"
/ovs/bin/ovs-ofctl add-flow br7 priority=2,in_port=48,dl_type=0x0800,nw_tos=0x03,actions=output:50
/ovs/bin/ovs-ofctl add-flow br7 priority=2,in_port=51,actions=output:50
/ovs/bin/ovs-ofctl add-flow br7 priority=2,in_port=50,dl_type=0x0800,nw_tos=0x03,actions=output:48
/ovs/bin/ovs-ofctl add-flow br7 priority=1,in_port=50,actions=output:51
