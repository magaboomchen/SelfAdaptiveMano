#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.slo import *
from sam.base.vnf import *


SFC_DOMAIN_PREFIX = "10.0.0.0"
SFC_DOMAIN_PREFIX_LENGTH = 8    # DO NOT MODIFY THIS VALUE,
    # otherwise BESS will incurr error
SFCID_LENGTH = 12  # DO NOT MODIFY THIS VALUE, otherwise BESS will incurr error

APP_TYPE_NORTHSOUTH_WEBSITE = "APP_TYPE_NORTHSOUTH_WEBSITE"

MANUAL_SCALE = 0
ADAPTIVE_SCALE = 1

STATE_IN_PROCESSING = "STATE_IN_PROCESSING"
STATE_ACTIVE = "STATE_ACTIVE"
STATE_INACTIVE = "STATE_INACTIVE"   # There maybe some resource used in DCN
STATE_DELETED = "STATE_DELETED" # All resource of this sfc/sfci has been released
# Delete an sfc/sfci will not release SFCIID
# To get back SFCIID, please prune sfc/sfci from database


class SFCI(object):
    def __init__(self, sfciID, vnfiSequence, sloRealTimeValue=None,
            forwardingPathSet=None):
        self.sfciID = sfciID
        self.vnfiSequence = vnfiSequence    # only show the direction1
        self.sloRealTimeValue = sloRealTimeValue
        self.forwardingPathSet = forwardingPathSet

    def __str__(self):
        string = "{0}\n".format(self.__class__)
        for key,values in self.__dict__.items():
            string = string + "{0}:{1}\n".format(key, values)
        return string

    def __repr__(self):
        return str(self)


class SFC(object):
    def __init__(self, sfcUUID, vNFTypeSequence, maxScalingInstanceNumber,
            backupInstanceNumber, applicationType, directions=None,
            attributes={}, traffic=None, slo=None, scalingMode=MANUAL_SCALE, sFCIs=[]):
        self.sfcUUID = sfcUUID
        self.vNFTypeSequence = vNFTypeSequence # [FW, LB]
        self.scalingMode = scalingMode
        self.maxScalingInstanceNumber = maxScalingInstanceNumber # 2
        self.backupInstanceNumber = backupInstanceNumber # 1
        self.applicationType = applicationType # NORTHSOUTH_WEBSITE
        self.slo = slo
        self.attributes = attributes # {"zone":ZONENAME}
        self.directions = directions

        # directions' data structure
        # [
        # {
        # 'ID': 0   # forwarding direction
        # 'source' : Outside
        #       {'IPv4':"0.0.0.0"} or {'MPLS':srcLable} or
        #       other routing addressing format
        # 'ingress': Any 
        #       May be a P4 switch or a server
        # 'match': {{},{},...} 
        #       classifier's match, 
        #       generic match fields: {"offset":offset, 
        #           "size":size, "value": value}
        # 'egress' : Any 
        #       May be a P4 switch or a server
        # 'destination': websiteIP
        #       {'IPv4':"0.0.0.0"} or
        # {'MPLS':srcLable} or other routing addressing format
        # },
        # {
        # 'ID': 1   # reverse direction
        # 'source' : WEBSITE
        #       {'IPv4':"0.0.0.0"} or {'MPLS':srcLable} or
        #       other routing addressing format
        # 'ingress': Any
        #       May be a P4 switch or a server
        # 'match': {{},{},...}
        #       classifier's match, generic match fields: {"offset":offset,
        #           "size":size, "value": value}
        # 'egress': Any
        #       May be a P4 switch or a server
        # 'destination': Outside
        #       {'IPv4':"0.0.0.0"} or {'MPLS':srcLable} or
        #       other routing addressing format
        # }
        # ]

        # following member is created by orchestrator
        self.sFCIs = sFCIs  # {SFCIID:active, SFCIID:active},
                            # For switch, we use pathID to distinguish
                            # different direction; 
                            # For bess, we use (src,dst) pair to distinguish
                            # different direction.

    def getSFCLength(self):
        return len(self.vNFTypeSequence)

    def getSFCTrafficDemand(self):
        return self.slo.throughput

    def __str__(self):
        string = "{0}\n".format(self.__class__)
        for key,values in self.__dict__.items():
            string = string + "{0}:{1}\n".format(key, values)
        return string

    def __repr__(self):
        return str(self)
