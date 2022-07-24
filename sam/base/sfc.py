#!/usr/bin/python
# -*- coding: UTF-8 -*-

SFC_DOMAIN_PREFIX = "10.0.0.0"
SFC_DOMAIN_PREFIX_LENGTH = 8  # DO NOT MODIFY THIS VALUE,
# otherwise BESS will incurr error
SFCID_LENGTH = 12  # DO NOT MODIFY THIS VALUE, otherwise BESS will incurr error

APP_TYPE_NORTHSOUTH_WEBSITE = "APP_TYPE_NORTHSOUTH_WEBSITE"
APP_TYPE_LARGE_BANDWIDTH = "APP_TYPE_LARGE_BANDWIDTH"
APP_TYPE_HIGH_AVA = "APP_TYPE_HIGH_AVA"
APP_TYPE_LOW_LATENCY = "APP_TYPE_LOW_LATENCY"
APP_TYPE_LARGE_CONNECTION = "APP_TYPE_LARGE_CONNECTION"
APP_TYPE_BEST_EFFORT = "APP_TYPE_BEST_EFFORT"

MANUAL_SCALE = "MANUAL_SCALE"
AUTO_SCALE = "AUTO_SCALE"

WITHOUT_PROTECTION = "WITHOUT_PROTECTION"
WITH_PROTECTION = "WITH_PROTECTION"

MANUAL_RECOVERY = "MANUAL_RECOVERY"
AUTO_RECOVERY = "AUTO_RECOVERY"

STATE_IN_PROCESSING = "STATE_IN_PROCESSING"
STATE_INIT_FAILED = "STATE_INIT_FAILED"
STATE_ACTIVE = "STATE_ACTIVE"
STATE_INACTIVE = "STATE_INACTIVE"  # There maybe some resource used in DCN
STATE_DELETED = "STATE_DELETED"  # All resource of this sfc/sfci has been released
# Warning: Delete an sfc/sfci will not release SFCIID
# To get back SFCIID, please prune sfc/sfci from database
STATE_RECOVER_MODE = "STATE_RECOVER_MODE"  # when a failure happen, sfc/sfci will be in this state
STATE_SCALING_OUT_MODE = "STATE_SCALING_OUT_MODE"  # when the sfc is scaling out, sfc will be in this state
STATE_SCALING_IN_MODE = "STATE_SCALING_IN_MODE" 

# SFCIID allocation
DASHBOARD_SFCIID_ALLOCATED_RANGE = [1, 9999]
REGULATOR_SFCIID_ALLOCATED_RANGE = [10000, 20000]


class SFCI(object):
    def __init__(self, sfciID, vnfiSequence=None, sloRealTimeValue=None,
                    forwardingPathSet=None, routingMorphic=None):
        self.sfciID = sfciID               # not uuid! It's a integer
        self.vnfiSequence = vnfiSequence  # only show the direction1
        self.sloRealTimeValue = sloRealTimeValue
        self.forwardingPathSet = forwardingPathSet
        self.routingMorphic = routingMorphic

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
            "forwardingPath": self.forwardingPathSet.primaryForwardingPath[1],
            "routingMorphic": self.routingMorphic
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
                 attributes=None, slo=None, 
                 scalingMode=AUTO_SCALE, routingMorphic=None,
                 protectionMode=WITHOUT_PROTECTION, recoveryMode=AUTO_RECOVERY,
                 vnfSequence=None, vnfiResourceQuota=None):
        self.sfcUUID = sfcUUID
        self.vNFTypeSequence = vNFTypeSequence  # [FW, LB]
        self.vnfSequence = vnfSequence
        self.scalingMode = scalingMode
        self.vnfiResourceQuota = vnfiResourceQuota  # VNFI_RESOURCE_QUOTA_SMALL
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
        # 'source': None, if tenant hasn't assign this, 
        #                  default setting assume that the
        #                  traffic come from outside,
        #                  orchestrator will assign a DCN
        #                  gateway switch's port as the source,
        #                  e.g. {'node': None or Switch(),
        #                           'IPv4':"*"}
        #           {'node': Server(), 'IPv4':"3.3.3.3"},
        #                 if tenants assign to their server,
        #                 e.g. their database
        # 'ingress': Any 
        #       May be a P4 switch or a server
        # 'match': {{},{},...} 
        #       classifier's match, 
        #       generic match fields: {"offset":offset, 
        #           "size":size, "value": value}
        # 'egress' : Any 
        #       May be a P4 switch or a server
        # 'destination': None, if tenant hasn't assign this, 
        #                  default setting assume traffic 
        #                  come to outside. In this condition,
        #                  destination is same as source;
        #           {'node': Server(), 'IPv4':"5.5.5.5"},
        #                 if tenants assign to their server,
        #                 e.g. their website
        # },
        # {
        # 'ID': 1   # reverse direction
        # 'source' : same as destination above
        # 'ingress': Any
        #       May be a P4 switch or a server
        # 'match': {{},{},...}
        #       classifier's match, generic match fields: {"offset":offset,
        #           "size":size, "value": value}
        # 'egress': Any
        #       May be a P4 switch or a server
        # 'destination': same as source above
        # }
        # ]

    def getSFCLength(self):
        return len(self.vNFTypeSequence)

    def getSFCTrafficDemand(self):
        return self.slo.throughput

    def getSFCLatencyBound(self):
        return self.slo.latency

    def isFixedResourceQuota(self):
        return self.vnfiResourceQuota != None

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
