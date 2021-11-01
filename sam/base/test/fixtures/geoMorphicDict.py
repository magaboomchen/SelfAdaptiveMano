#!/usr/bin/python
# -*- coding: UTF-8 -*-

import numpy as np 


geoMorphicDictTemplate = {
            "morphicName": "geo",
            "identifierName": "longitude",
            "headerOffsets": 14,
            "headerBits": 128,
            "etherType": 0xA000,
            "nshProtocolNumber": 0x07,
            "ipProto": 0x90,
            "metadataDict": {
                "longitude": {
                    "type": np.float64,
                    "offset": 14,
                    "bits": 64,
                    "value": 0,
                    "humanReadable": "30"
                },
                "latitude": {
                    "type": np.float64,
                    "offset": 22,
                    "bits": 64,
                    "value": 0,
                    "humanReadable": "120"
                }
            },
            "commonField": {
                "totalLength": {
                    "type": np.uint16,
                    "offset": 30,
                    "bits": 16,
                    "value": 0
                },
                "nextHeaderProtocol": {
                    "type": np.uint8,
                    "offset": 32,
                    "bits": 8,
                    "value": 0
                }
            }
        }