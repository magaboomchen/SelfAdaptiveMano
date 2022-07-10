#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
https://docs.nvidia.com/networking/pages/viewpage.action?pageId=19798092
https://support.mellanox.com/s/article/lrh-and-grh-infiniband-headers
'''

import numpy as np

from sam.base.routingMorphic import ROCEV1_ROUTE_PROTOCOL


roceV1MorphicDictTemplate = {
            "morphicName": ROCEV1_ROUTE_PROTOCOL,
            "identifierName": "DGID",
            "headerOffsets": 14,
            "headerBits": 320,
            "etherType": 0x8915,
            "nshProtocolNumber": 0x02,
            "ipProto": 0x29,
            "metadataDict": {
                "SGID": {
                    "type": np.uint32,
                    "offset": 26,
                    "bits": 128,
                    "value": 0,
                    "humanReadable": "fe80::eef4:bbff:feda:3944"
                },
                "DGID": {
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