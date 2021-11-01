#!/usr/bin/python
# -*- coding: UTF-8 -*-

import numpy as np 


idMorphicDictTemplate = {
            "morphicName": "id",
            "identifierName": "longitude",
            "headerOffsets": 14,
            "headerBits": 128,
            "etherType": 0xA002,
            "nshProtocolNumber": 0x06,
            "ipProto": 0x92,
            "metadataDict": {
                "id": {
                    "type": np.int32,
                    "offset": 14,
                    "bits": 32,
                    "value": 0,
                    "humanReadable": "0"
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