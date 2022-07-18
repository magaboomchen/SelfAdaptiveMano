#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
https://tools.ietf.org/id/draft-ietf-sfc-nsh-17.html
Next protocol
0x0: Unassigned
0x1: IPv4
0x2: IPv6
0x3: Ethernet
0x4: NSH
0x5: MPLS
0x6: ROCEv1
0xFE: Experiment 1
0xFF: Experiment 2
'''

import numpy as np

from sam.base.routingMorphic import NSH_ROUTE_PROTOCOL


srv6MorphicDictTemplate = {
            "morphicName": NSH_ROUTE_PROTOCOL,
            "identifierName": "SPISI",
            "headerOffsets": 14,
            "headerBits": 192,
            "etherType": 0x894F,
            "nshProtocolNumber": 0x04,
            "ipProto": 0xFF,
            "metadataDict": {
                "SPISI": {
                    "type": np.uint32,
                    "offset": 26,
                    "bits": 128,
                    "value": 0,
                    "humanReadable": "257"
                }
            },
            "commonField": {
                "VerTTLLength": {
                    "type": np.uint16,
                    "offset": 0,
                    "bits": 16,
                    "value": 0
                },
                "MDType": {
                    "type": np.uint8,
                    "offset": 8,
                    "bits": 8,
                    "value": 0
                },
                "NextProtocol": {
                    "type": np.uint8,
                    "offset": 8,
                    "bits": 8,
                    "value": 0
                },
            }
        }