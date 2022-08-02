#!/usr/bin/python
# -*- coding: UTF-8 -*-

from typing import Union

from sam.base.routingMorphic import IPV4_ROUTE_PROTOCOL, IPV6_ROUTE_PROTOCOL, ROCEV1_ROUTE_PROTOCOL, SRV6_ROUTE_PROTOCOL

ACL_PROTO_TCP = 6
ACL_PROTO_UDP = 17
ACL_PROTO_ICMP = 1
ACL_PROTO_IGMP = 2
ACL_PROTO_IPIP = 4

ACL_ACTION_ALLOW = 0
ACL_ACTION_DENY = 1

'''
This file defines the format of rules used for firewall et al. 
In vnfi, rules are maintained as a list of ACLTuple in vnfi.config['ACL']
'''


class ACLTuple(object):
    def __init__(self, action, proto=None, srcAddr=None, dstAddr=None, srcPort=None, dstPort=None):
        # type: (Union[ACL_ACTION_ALLOW, ACL_ACTION_DENY], Union[ACL_PROTO_TCP, ACL_PROTO_UDP], str, str, tuple[int, int], tuple[int, int]) -> None

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
        if self.proto is not None:
            entries.append('ip proto %d' % self.proto)
        '''
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
        '''
        if self.srcAddr is not None:
            entries.append('src %s' % self.srcAddr)
        if self.dstAddr is not None:
            entries.append('dst %s' % self.dstAddr)
        if self.srcPort is not None:
            if self.srcPort[0] is not None and self.srcPort[0] != 0:
                entries.append('src port >= %d' % self.srcPort[0])
            if self.srcPort[1] is not None and self.srcPort[1] != 65535:
                entries.append('src port <= %d' % self.srcPort[1])
        if self.dstPort is not None:
            if self.dstPort[0] is not None and self.dstPort[0] != 0:
                entries.append('dst port >= %d' % self.dstPort[0])
            if self.dstPort[1] is not None and self.dstPort[1] != 65535:
                entries.append('dst port <= %d' % self.dstPort[1])
        line = line + ' %s' % entries[0]
        for entry in entries[1:]:
            line = line + ' && %s' % entry
        return line

    def gen128BitsDstIdentifierFWLine(self):
        if self.action == ACL_ACTION_ALLOW:
            action = 1
        elif self.action == ACL_ACTION_DENY:
            action = 0
        else:
            action = 0

        if self._isWildcard():
            line = '::0/0 ::0 {0}'.format(action)
            return line

        line = "{0} {1}".format(self.dstAddr, action)
        return line

    def __hash__(self):
        hashList = []
        for memberName in self.__dict__.keys():
            member = getattr(self, memberName)
            if member == None:
                hashList.append(-1)
            else:
                hashList.append(member)
        return hash(tuple(hashList))

    def __eq__(self, other):
        for memberName in self.__dict__.keys():
            selfMember = getattr(self, memberName)
            otherMember = getattr(other, memberName)
            if selfMember != otherMember:
                return False
        return True


class ACLTable(object):
    def __init__(self):
        self.ipv4RulesList = []
        self.ipv6RulesList = []
        self.srv6RulesList = []
        self.rocev1RulesList = []

    def addRules(self, aclRule, routeProtocol):
        # type: (ACLTuple, Union[IPV4_ROUTE_PROTOCOL, IPV6_ROUTE_PROTOCOL, SRV6_ROUTE_PROTOCOL, ROCEV1_ROUTE_PROTOCOL]) -> None
        if routeProtocol == IPV4_ROUTE_PROTOCOL:
            self.ipv4RulesList.append(aclRule)
        elif routeProtocol == IPV6_ROUTE_PROTOCOL:
            self.ipv6RulesList.append(aclRule)
        elif routeProtocol == SRV6_ROUTE_PROTOCOL:
            self.srv6RulesList.append(aclRule)
        elif routeProtocol == ROCEV1_ROUTE_PROTOCOL:
            self.rocev1RulesList.append(aclRule)
        else:
            raise ValueError("Unknown route protocol {0}".format(routeProtocol))

    def getRulesNum(self, routeProtocol):
        # type: (Union[IPV4_ROUTE_PROTOCOL, IPV6_ROUTE_PROTOCOL, SRV6_ROUTE_PROTOCOL, ROCEV1_ROUTE_PROTOCOL]) -> int
        if routeProtocol == IPV4_ROUTE_PROTOCOL:
            return len(self.ipv4RulesList)
        elif routeProtocol == IPV6_ROUTE_PROTOCOL:
            return len(self.ipv6RulesList)
        elif routeProtocol == SRV6_ROUTE_PROTOCOL:
            return len(self.srv6RulesList)
        elif routeProtocol == ROCEV1_ROUTE_PROTOCOL:
            return len(self.rocev1RulesList)
        else:
            raise ValueError("Unknown route protocol {0}".format(routeProtocol))

    def getIPv4RulesNum(self):
        return len(self.ipv4RulesList)
    
    def get128BitsRulesNum(self):
        return len(self.ipv6RulesList) + len(self.srv6RulesList) + len(self.rocev1RulesList)

    def getRulesList(self, routeProtocol):
        # type: (Union[IPV4_ROUTE_PROTOCOL, IPV6_ROUTE_PROTOCOL, SRV6_ROUTE_PROTOCOL, ROCEV1_ROUTE_PROTOCOL]) -> list(ACLTuple)
        if routeProtocol == IPV4_ROUTE_PROTOCOL:
            return self.ipv4RulesList
        elif routeProtocol == IPV6_ROUTE_PROTOCOL:
            return self.ipv6RulesList
        elif routeProtocol == SRV6_ROUTE_PROTOCOL:
            return self.srv6RulesList
        elif routeProtocol == ROCEV1_ROUTE_PROTOCOL:
            return self.rocev1RulesList
        else:
            raise ValueError("Unknown route protocol {0}".format(routeProtocol))

    def parseACLFile(self, path):
        # type: (str) -> list(ACLTuple)
        res = []
        with open(path, 'r') as f:
            for line in f.readlines():
                line = line.strip().split()
                #print(line)
                srcAddr = line[0][1:]
                if srcAddr in ['0.0.0.0/0', "::0/0"]:
                    srcAddr = None
                dstAddr = line[1]
                if dstAddr in ['0.0.0.0/0', "::0/0"]:
                    dstAddr = None
                srcPort = (int(line[2]), int(line[4]))
                if srcPort == (0, 65535):
                    srcPort = None
                dstPort = (int(line[5]), int(line[7]))
                if dstPort == (0, 65535):
                    dstPort = None 
                proto = int(line[8][:4], 16)
                if proto == 0:
                    proto = None
                acl = ACLTuple(0, proto, srcAddr, dstAddr, srcPort, dstPort)
                res.append(acl)
                #print(acl.genFWLine())
        return res


if __name__ == '__main__':
    # for test
    acl1 = ACLTuple(0, 1, '192.168.0.2', '2.0.0.8/24', (0,1024), (5982, 5982))
    print(acl1.genFWLine())
    acl1.__hash__()
    acl2 = ACLTuple(1, None, None, '2.0.0.8/24', (0,1024), (None, 5982))
    print(acl2.genFWLine())
    acl2.__hash__()
    print(acl2.__eq__(acl1))
    acl3 = ACLTuple(0, None, None, '2.0.0.8/24', None, None)
    print(acl3.genFWLine())
    acl3.__hash__()
    acl4 = ACLTuple(0, 2, None, None, None, None)
    print(acl4.genFWLine())
    acl4.__hash__()
    acl5 = ACLTuple(0, None, None, None, (1024, None), None)
    print(acl5.genFWLine())
    acl5.__hash__()

    # fileName = sys.argv[1]
    # aclT = ACLTable()
    # acls = aclT.parseACLFile(fileName)
    # with open('statelessFW', 'w') as f:
    #     for each in acls:
    #         f.write(each.genFWLine())
    #         f.write('\n')