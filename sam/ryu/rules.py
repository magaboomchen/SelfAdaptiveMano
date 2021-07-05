#!/usr/bin/python
# -*- coding: UTF-8 -*-

import ipaddress


class Rule(object):
    def __init__(self, prefix, length, nexthop, v6=False):
        self.prefix = prefix
        self.length = length
        self.nexthop = nexthop
        self.v6 = v6

    def int2addr(self, num):
        if self.v6:
            return str(ipaddress.IPv6Address(num))
        return str(ipaddress.IPv4Address(num))

    def __str__(self):
        return '%s/%d, %s' % (self.int2addr(self.prefix),
                                self.length,
                                self.nexthop)
