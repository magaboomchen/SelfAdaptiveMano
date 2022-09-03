#!/usr/bin/python
# -*- coding: UTF-8 -*-

from typing import Union

ETH_TYPE_IPV4 = 0x0800
ETH_TYPE_IPV6 = 0x86DD
ETH_TYPE_ROCEV1 = 0x8915
ETH_TYPE_NSH = 0x894F


class P4Match(object):
    def __init__(self,
                 etherType=None,   # type: Union[ETH_TYPE_IPV4, ETH_TYPE_IPV6, ETH_TYPE_ROCEV1, ETH_TYPE_NSH, None]
                 src=None,         # type: Union[int, None]
                 srcMask=None,      # type: Union[int, None]
                 dst=None,         # type: Union[int, None]
                 dstMask=None,      # type: Union[int, None]
                 nsh=None         # type: Union[int, None]
                 ):
        self.etherType = etherType
        self.src = src  # IPv4: 32bits
                        # IPv6: 128bits
                        # SRv6: 128bits
                        # RoceV1: 128bits
                        # None: don't care this field
        self.srcMask = srcMask
        self.dst = dst  # IPv4: 32bits
                        # IPv6: 128bits
                        # SRv6: 128bits
                        # RoceV1: 128bits
                        # None: don't care this field
        self.dstMask = dstMask
        self.nsh = nsh  # SPI+SI
