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

echo "add bridge"
ovs-vsctl add-br br1 -- set bridge br1 datapath_type=pica8 protocols=OpenFlow13
ovs-vsctl add-br br2 -- set bridge br2 datapath_type=pica8 protocols=OpenFlow13
ovs-vsctl add-br br3 -- set bridge br3 datapath_type=pica8 protocols=OpenFlow13

echo "set bridge"
ovs-vsctl set bridge br1 other_config:datapath-id=0000000000000001
ovs-vsctl set bridge br2 other_config:datapath-id=0000000000000002
ovs-vsctl set bridge br3 other_config:datapath-id=0000000000000003

ovs-vsctl set bridge br1 other_config:disable-in-band=true
ovs-vsctl set bridge br2 other_config:disable-in-band=true
ovs-vsctl set bridge br3 other_config:disable-in-band=true

addPort()
{
    echo "add interface" $2 "to bridge" $1
    ovs-vsctl add-port $1 $2 vlan_mode=trunk tag=1 -- set interface $2 type=pica8
}

addPort br1 ge-1/1/25
addPort br1 ge-1/1/26
addPort br1 ge-1/1/27
addPort br1 ge-1/1/28
addPort br1 ge-1/1/29

addPort br2 ge-1/1/31
addPort br2 ge-1/1/33
addPort br2 ge-1/1/35
addPort br2 te-1/1/49

addPort br3 ge-1/1/37
addPort br3 ge-1/1/39
addPort br3 ge-1/1/41

echo "del-flows"
ovs-ofctl del-flows br1
ovs-ofctl del-flows br2
ovs-ofctl del-flows br3

echo "set controller"
ovs-vsctl set-controller br1 tcp:192.168.0.194:6633
ovs-vsctl set-controller br2 tcp:192.168.0.194:6633
ovs-vsctl set-controller br3 tcp:192.168.0.194:6633
