#!/usr/bin/python
# -*- coding: UTF-8 -*-

import numpy as np 


ipv4MorphicDictTemplate = {
            "morphicName": "IPv4",
            "identifierName": "dstIP",
            "headerOffsets": 14,
            "headerBits": 160,
            "etherType": 0x0800,
            "ipProto": 0x04,
            "metadataDict": {
                "srcIP": {
                    "type": np.uint32,
                    "offset": 26,
                    "bits": 32,
                    "value": 167772162,
                    "humanReadable": "10.0.0.2"
                },
                "dstIP": {
                    "type": np.uint32,
                    "offset": 30,
                    "bits": 32,
                    "value": 168820992,
                    "humanReadable": "10.16.1.1"
                }
            },
            "commonField": {
                "totalLength": {
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