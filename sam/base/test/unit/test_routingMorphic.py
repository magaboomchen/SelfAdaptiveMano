#!/usr/bin/python
# -*- coding: UTF-8 -*-

import uuid
import numpy
import logging
import struct

import pytest

from sam.base.server import *
from sam.base.command import *
from sam.base.messageAgent import *
from sam.base.routingMorphic import *
from sam.base.socketConverter import SocketConverter, BCAST_MAC
from sam.test.testBase import *
from sam.base.test.fixtures.ipv4MorphicDict import ipv4MorphicDictTemplate
from sam.base.test.fixtures.ipv6MorphicDict import ipv6MorphicDictTemplate
from sam.base.test.fixtures.geoMorphicDict import geoMorphicDictTemplate

MANUAL_TEST = True

logging.basicConfig(level=logging.INFO)


class TestRoutingMorphicClass(TestBase):
    def setup_method(self, method):
        """ setup any state tied to the execution of the given method in a
        class.  setup_method is invoked for every test method of a class.
        """
        self.geoMorphicDictTemplate = geoMorphicDictTemplate
        self.ipv4MorphicDictTemplate = ipv4MorphicDictTemplate
        self.ipv6MorphicDictTemplate = ipv6MorphicDictTemplate
        self._sc = SocketConverter()

    def teardown_method(self, method):
        """ teardown any state that was previously setup with a setup_method
        call.
        """
        pass

    def test_convertMatchFieldsDict(self):
        self.rm = RoutingMorphic()
        self.rm.from_dict(self.ipv4MorphicDictTemplate)
        # print(self.rm.metadataDict)

        matchFiledsDict = {
            "dstIP": self._sc.ip2int("1.1.1.1")
        }

        matchOffsetBitsList = self.rm.convertMatchFieldsDict(matchFiledsDict)
        # assert matchOffsetBitsList[0]["mask"] == b'\xFF\xFF\xFF\xFF'
        assert matchOffsetBitsList == [
            {
                "offset": 30,
                "bits": 32,
                "value": "{0:b}".format(self._sc.ip2int("1.1.1.1")),
                "mask": b'\xFF\xFF\xFF\xFF'
            }
        ]

        # print(self._sc.ip2int("10.0.0.1"))

    def test_encodeIDForSFC(self):
        self.rm = RoutingMorphic()
        self.rm.from_dict(self.ipv4MorphicDictTemplate)

        assert self.rm.encodeIdentifierForSFC(1, 1) == self._sc.ip2int("10.16.1.0")
        assert self.rm.value2HumanReadable(168820992) == "10.16.1.0"
        assert self.rm.decodeIdentifierDictForSFC(self.rm.getIdentifierDict()) == (1, 1)
