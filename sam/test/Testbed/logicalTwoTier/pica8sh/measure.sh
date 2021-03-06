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
ovs-vsctl add-br br7 -- set bridge br7 datapath_type=pica8 protocols=OpenFlow13

echo "set bridge"
ovs-vsctl set bridge br7 other_config:datapath-id=0000000000000007

ovs-vsctl set bridge br7 other_config:disable-in-band=true

addPort()
{
    echo "add interface" $2 "to bridge" $1
    ovs-vsctl add-port $1 $2 vlan_mode=trunk tag=1 -- set interface $2 type=pica8
}


addPort br7 ge-1/1/48
addPort br7 te-1/1/49
addPort br7 te-1/1/50
addPort br7 te-1/1/51

echo "del-flows"
ovs-ofctl del-flows br7

echo "loop inbound"
/ovs/bin/ovs-ofctl add-flow br7 priority=2,in_port=51,actions=output:50
/ovs/bin/ovs-ofctl add-flow br7 priority=2,in_port=49,actions=output:51
