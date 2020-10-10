#!/usr/bin/python
# -*- coding: UTF-8 -*-

ACL_PROTO_TCP = 0
ACL_PROTO_UDP = 1
ACL_PROTO_ICMP = 2
ACL_PROTO_IGMP = 3
ACL_PROTO_IPIP = 4

ACL_ACTION_ALLOW = 0
ACL_ACTION_DENY = 1

'''
This file defines the format of rules used for firewall et al. 
In vnfi, rules are maintained as a list of ACLTuple in vnfi.config['ACL']
'''

class ACLTuple(object):
    def __init__(self, action, proto=None, srcAddr=None, dstAddr=None, srcPort=None, dstPort=None):

        self.action = action

        self.proto = proto

        # srcAddr and dstAddr must be XX.XX.XX.XX/XX or XX.XX.XX.XX
        self.srcAddr = srcAddr
        self.dstAddr = dstAddr
        
        # srcPort and dstPort must be a tuple (minPort, maxPort) which is a closed interval except that one is None.
        self.srcPort = srcPort
        self.dstPort = dstPort

    def _isWildcard(self):
        return self.proto is None and self.srcAddr is None and self.dstAddr is None and self.srcPort is None and self.dstPort is None

    def genFWLine(self):
        if self.action == ACL_ACTION_ALLOW:
            line = 'allow'
        elif self.action == ACL_ACTION_DENY:
            line = 'deny'
        if self._isWildcard():
            line = line + ' all'
            return line
        entries = []
        if self.proto == ACL_PROTO_ICMP:
            entries.append('icmp')
        elif self.proto == ACL_PROTO_IGMP:
            entries.append('igmp')
        elif self.proto == ACL_PROTO_IPIP:
            entries.append('ipip')
        elif self.proto == ACL_PROTO_TCP:
            entries.append('tcp')
        elif self.proto == ACL_PROTO_UDP:
            entries.append('udp')
        if self.srcAddr is not None:
            entries.append('src %s' % self.srcAddr)
        if self.dstAddr is not None:
            entries.append('dst %s' % self.dstAddr)
        if self.srcPort is not None:
            if self.srcPort[0] is not None:
                entries.append('src port >= %d' % self.srcPort[0])
            if self.srcPort[1] is not None:
                entries.append('src port <= %d' % self.srcPort[1])
        if self.dstPort is not None:
            if self.dstPort[0] is not None:
                entries.append('dst port >= %d' % self.dstPort[0])
            if self.dstPort[1] is not None:
                entries.append('dst port <= %d' % self.dstPort[1])
        line = line + ' %s' % entries[0]
        for entry in entries[1:]:
            line = line + ' && %s' % entry
        return line

if __name__ == '__main__':
    ''' test '''
    acl1 = ACLTuple(0, 1, '192.168.0.2', '2.0.0.8/24', (0,1024), (5982, 5982))
    print(acl1.genFWLine())
    acl2 = ACLTuple(1, None, None, '2.0.0.8/24', (0,1024), (None, 5982))
    print(acl2.genFWLine())
    acl3 = ACLTuple(0, None, None, '2.0.0.8/24', None, None)
    print(acl3.genFWLine())
    acl4 = ACLTuple(0, 2, None, None, None, None)
    print(acl4.genFWLine())
    acl5 = ACLTuple(0, None, None, None, (1024, None), None)
    print(acl5.genFWLine())