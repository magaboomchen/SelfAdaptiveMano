#!/usr/bin/python
# -*- coding: UTF-8 -*-

import numpy as np

from sam.base.routingMorphic import *


class Flow(object):
    def __init__(self, identifierDict, trafficRate=None, trafficBandwidth=None):
        self.identifierDict = identifierDict # Identifier of a flow. identifierValue of '10.0.0.1' is 167772161
        # Identifier dict format:
        # {
        #     "type": np.int32,
        #     "offset": 14,
        #     "bits": 32,
        #     "value": 167772161,
        #     "humanReadable": '10.0.0.1'
        # }
        # You can get identifier in <object sfc>.routingMorphic.getIdentifierDict() in <object cmd>.attributes['sfc']
        # For a flow of a 'sfci' with in the stage of 'vnf', you can use routingMorphic.encodeIdentifierForSFC() method to get identiferValue.
        # You can get 'humanReadable' item in identifierDict using routingMorphic.value2HumanReadable().
        self.advantagePointList = []    # a list of advantage point which measured this flow, e.g. switchID
        self.trafficRate = trafficRate  # Unit: Mpps, packet per seconds
        self.trafficBandwidth = trafficBandwidth # Unit: Mbps, bit per seconds

    def __str__(self):
        string = "{0}\n".format(self.__class__)
        for key,values in self.__dict__.items():
            string = string + "{0}:{1}\n".format(key, values)
        return string

    def __repr__(self):
        return str(self)
