#!/bin/sh

echo "delete bridge"
ovs-vsctl del-br br0
ovs-vsctl del-br br1
ovs-vsctl del-br br2

echo "add bridge"
ovs-vsctl add-br br0 -- set bridge br0 datapath_type=pica8 protocols=OpenFlow13
ovs-vsctl add-br br1 -- set bridge br1 datapath_type=pica8 protocols=OpenFlow13
ovs-vsctl add-br br2 -- set bridge br2 datapath_type=pica8 protocols=OpenFlow13

echo "set bridge"
ovs-vsctl set bridge br0 other_config:datapath-id=0000000000000001
ovs-vsctl set bridge br1 other_config:datapath-id=0000000000000002
ovs-vsctl set bridge br2 other_config:datapath-id=0000000000000003

ovs-vsctl set bridge br0 other_config:disable-in-band=true
ovs-vsctl set bridge br1 other_config:disable-in-band=true
ovs-vsctl set bridge br2 other_config:disable-in-band=true

echo "add interface ge-1/1/1"
ovs-vsctl add-port br0 ge-1/1/1 vlan_mode=trunk tag=1 -- set interface ge-1/1/1 type=pica8

echo "add interface ge-1/1/2"
ovs-vsctl add-port br0 ge-1/1/2 vlan_mode=trunk tag=1 -- set interface ge-1/1/2 type=pica8

echo "add interface te-1/1/49"
ovs-vsctl add-port br0 te-1/1/49 vlan_mode=trunk tag=1 -- set interface te-1/1/49 type=pica8

echo "add interface ge-1/1/25"
ovs-vsctl add-port br0 ge-1/1/25 vlan_mode=trunk tag=1 -- set interface ge-1/1/25 type=pica8

echo "add interface ge-1/1/35"
ovs-vsctl add-port br0 ge-1/1/35 vlan_mode=trunk tag=1 -- set interface ge-1/1/35 type=pica8

echo "add interface ge-1/1/32"
ovs-vsctl add-port br1 ge-1/1/32 vlan_mode=trunk tag=1 -- set interface ge-1/1/32 type=pica8

echo "add interface ge-1/1/34"
ovs-vsctl add-port br1 ge-1/1/34 vlan_mode=trunk tag=1 -- set interface ge-1/1/34 type=pica8

echo "add interface ge-1/1/36"
ovs-vsctl add-port br1 ge-1/1/36 vlan_mode=trunk tag=1 -- set interface ge-1/1/36 type=pica8

echo "add interface ge-1/1/26"
ovs-vsctl add-port br1 ge-1/1/26 vlan_mode=trunk tag=1 -- set interface ge-1/1/26 type=pica8

echo "add interface te-1/1/50"
ovs-vsctl add-port br2 te-1/1/50 vlan_mode=trunk tag=1 -- set interface te-1/1/50 type=pica8

echo "add interface ge-1/1/37"
ovs-vsctl add-port br2 ge-1/1/37 vlan_mode=trunk tag=1 -- set interface ge-1/1/37 type=pica8

echo "add interface ge-1/1/39"
ovs-vsctl add-port br2 ge-1/1/39 vlan_mode=trunk tag=1 -- set interface ge-1/1/39 type=pica8

echo "set controller"
ovs-vsctl set-controller br0 tcp:192.168.0.194:6633
ovs-vsctl set-controller br1 tcp:192.168.0.194:6633
ovs-vsctl set-controller br2 tcp:192.168.0.194:6633
