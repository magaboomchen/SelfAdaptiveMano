#!/usr/bin/python
# -*- coding: UTF-8 -*-

import numpy as np 


contentMorphicDictTemplate = {
            "morphicName": "content",
            "identifierName": "url",
            "headerOffsets": 14,
            "headerBits": 128,
            "etherType": 0xA001,
            "ipProto": 0x91,
            "metadataDict": {
                "url": {
                    "type": str,
                    "offset": 14,
                    "bits": 8*64,
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