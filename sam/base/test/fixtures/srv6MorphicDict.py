#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
https://www.segment-routing.net/images/201901-SRv6.pdf
'''

import numpy as np

from sam.base.routingMorphic import SRV6_ROUTE_PROTOCOL 


srv6MorphicDictTemplate = {
            "morphicName": SRV6_ROUTE_PROTOCOL,
            "identifierName": "dstIP",
            "headerOffsets": 14,
            "headerBits": 320,
            "etherType": 0x86DD,
            "nshProtocolNumber": 0x02,
            "ipProto": 0x29,
            "metadataDict": {
                "srcIP": {
                    "type": np.uint32,
                    "offset": 26,
                    "bits": 128,
                    "value": 0,
                    "humanReadable": "fe80::eef4:bbff:feda:3944"
                },
                "dstIP": {
                    "type": np.uint32,
                    "offset": 30,
                    "bits": 128,
                    "value": 0,
                    "humanReadable": "fe80::eef4:bbff:feda:3945"
                }
            },
            "commonField": {
                "payloadLength": {
                    "type": np.uint16,
                    "offset": 16,
                    "bits": 16,
                    "value": 0
                },
                "nextHeaderProtocol": {
                    "type": np.uint8,
                    "offset": 8,
                    "bits": 8,
                    "value": 0
                }
            }
        }