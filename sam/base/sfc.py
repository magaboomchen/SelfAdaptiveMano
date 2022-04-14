#!/usr/bin/python
# -*- coding: UTF-8 -*-

SFC_DOMAIN_PREFIX = "10.0.0.0"
SFC_DOMAIN_PREFIX_LENGTH = 8  # DO NOT MODIFY THIS VALUE,
# otherwise BESS will incurr error
SFCID_LENGTH = 12  # DO NOT MODIFY THIS VALUE, otherwise BESS will incurr error

APP_TYPE_NORTHSOUTH_WEBSITE = "APP_TYPE_NORTHSOUTH_WEBSITE"

MANUAL_SCALE = "MANUAL_SCALE"
ADAPTIVE_SCALE = "ADAPTIVE_SCALE"

WITHOUT_PROTECTION = "WITHOUT_PROTECTION"
WITH_PROTECTION = "WITH_PROTECTION"

MANUAL_RECOVERY = "MANUAL_RECOVERY"
AUTO_RECOVERY = "AUTO_RECOVERY"

STATE_IN_PROCESSING = "STATE_IN_PROCESSING"
STATE_ACTIVE = "STATE_ACTIVE"
STATE_INACTIVE = "STATE_INACTIVE"  # There maybe some resource used in DCN
STATE_DELETED = "STATE_DELETED"  # All resource of this sfc/sfci has been released
# Delete an sfc/sfci will not release SFCIID
# To get back SFCIID, please prune sfc/sfci from database
STATE_PROTECTION_MODE = "STATE_PROTECTION_MODE"  # when a failure happen, sfc/sfci will be in this state


# MORPHIC_IPV4 = "MORPHIC_IPV4"
# MORPHIC_IDENTITY = "MORPHIC_IDENTITY"
# MORPHIC_GEO = "MORPHIC_GEO"
# MORPHIC_CONTENT = "MORPHIC_CONTENT"


class SFCI(object):
    def __init__(self, sfciID, vnfiSequence=None, sloRealTimeValue=None,
                 forwardingPathSet=None):
        self.sfciID = sfciID
        self.vnfiSequence = vnfiSequence  # only show the direction1
        self.sloRealTimeValue = sloRealTimeValue
        self.forwardingPathSet = forwardingPathSet

    def getVNFTypeByStageNum(self, stageNum):
        if stageNum == len(self.vnfiSequence):
            return 0
        elif stageNum >= 0 and stageNum < len(self.vnfiSequence):
            return self.vnfiSequence[stageNum][0].vnfID
        else:
            raise ValueError("Invalid stageNum:{0}".format(stageNum))

    def to_dict(self):
        sfciDict = {
            "sfciID": self.sfciID,
            "vnfiSequenceLength": len(self.vnfiSequence),
            "forwardingPath": self.forwardingPathSet.primaryForwardingPath[1]
        }

        for vnfiIndex in range(len(self.vnfiSequence)):
            sfciDict["vnfi_{0}".format(vnfiIndex)] \
                = self.vnfiSequence[vnfiIndex][0].to_dict()

        return sfciDict

    def __str__(self):
        string = "{0}\n".format(self.__class__)
        for key, values in self.__dict__.items():
            string = string + "{0}:{1}\n".format(key, values)
        return string

    def __repr__(self):
        return str(self)


class SFC(object):
    def __init__(self, sfcUUID, vNFTypeSequence, maxScalingInstanceNumber,
                 backupInstanceNumber, applicationType, directions=None,
                 attributes=None, traffic=None, slo=None, sfChainMethod=None,
                 scalingMode=MANUAL_SCALE, sFCIs=None, routingMorphic=None,
                 protectionMode=WITHOUT_PROTECTION, recoveryMode=MANUAL_RECOVERY):
        self.sfcUUID = sfcUUID
        self.vNFTypeSequence = vNFTypeSequence  # [FW, LB]
        self.scalingMode = scalingMode
        self.maxScalingInstanceNumber = maxScalingInstanceNumber  # 2
        self.protectionMode = protectionMode
        self.backupInstanceNumber = backupInstanceNumber  # 1
        self.applicationType = applicationType  # NORTHSOUTH_WEBSITE
        self.recoveryMode = recoveryMode
        self.routingMorphic = routingMorphic
        self.slo = slo
        if attributes is None:
            self.attributes = {}
        else:
            self.attributes = attributes  # {"zone":ZONENAME}
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
        if sFCIs is None:
            self.sFCIs = []
        else:
            self.sFCIs = sFCIs  # {SFCIID:active, SFCIID:active},
        # For switch, we use pathID to distinguish
        # different direction;
        # For bess, we use (src, dst) pair to distinguish
        # different direction.

    def getSFCLength(self):
        return len(self.vNFTypeSequence)

    def getSFCTrafficDemand(self):
        return self.slo.throughput

    def getSFCLatencyBound(self):
        return self.slo.latencyBound

    def to_dict(self):
        return {
            'sfcUUID': str(self.sfcUUID),
            'vNFTypeSequence': self.vNFTypeSequence,
            'zone': self.attributes['zone'],  # "PROJECT3_ZONE"
            'source': self.directions[0]['source'],
            # Outside, {'IPv4':"0.0.0.0"} or {'MPLS':srcLable} or
            # other routing addressing format
            'ingress': self.directions[0]['ingress'].getServerID(),
            # Any May be a P4 switch or a server
            'match': self.directions[0]['match'],
            # {{},{},...}
            # classifier's match,
            # generic match fields: {"offset":offset,
            # "size":size, "value": value}
            'egress': self.directions[0]['egress'].getServerID(),
            # Any, May be a P4 switch or a server
            'destination': self.directions[0]['destination'],
            # websiteIP
            # {'IPv4':"0.0.0.0"} or
            # {'MPLS':srcLable} or other routing addressing format
            'routingMorphic': self.routingMorphic
        }

    def __str__(self):
        string = "{0}\n".format(self.__class__)
        for key, values in self.__dict__.items():
            string = string + "{0}:{1}\n".format(key, values)
        return string

    def __repr__(self):
        return str(self)
