#!/usr/bin/python
# -*- coding: UTF-8 -*-

from uuid import UUID
from typing import Any, Dict, List, Union

from sam.base.direction import Direction
from sam.base.slo import SLO
from sam.base.path import ForwardingPathSet
from sam.base.routingMorphic import RoutingMorphic
from sam.base.vnf import VNF, VNF_TYPE_FW, VNF_TYPE_LB, VNFI, \
            VNFI_RESOURCE_QUOTA_LARGE, VNFI_RESOURCE_QUOTA_SMALL
from sam.base.sfcConstant import APP_TYPE_LARGE_BANDWIDTH, \
            APP_TYPE_NORTHSOUTH_WEBSITE, AUTO_SCALE, AUTO_RECOVERY, \
            MANUAL_RECOVERY, MANUAL_SCALE, SFC_DIRECTION_0, SFC_DIRECTION_1, WITH_PROTECTION, \
            WITHOUT_PROTECTION


class SFCI(object):
    def __init__(self, sfciID,          # type: int
                vnfiSequence=None,      # type: List[List[VNFI]]
                sloRealTimeValue=None,  # type: SLO
                forwardingPathSet=None, # type: ForwardingPathSet
                routingMorphic=None     # type: RoutingMorphic
                ):
        self.sfciID = sfciID
        self.vnfiSequence = vnfiSequence  # only show the direction0
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
    def __init__(self, sfcUUID,     # type: UUID
                vNFTypeSequence,    # type: list(Union[VNF_TYPE_FW, VNF_TYPE_LB])
                maxScalingInstanceNumber,   # type: int
                backupInstanceNumber,       # type: int
                applicationType,            # type: Union[APP_TYPE_NORTHSOUTH_WEBSITE, APP_TYPE_LARGE_BANDWIDTH]
                directions=None,            # type: Dict[Union[SFC_DIRECTION_0, SFC_DIRECTION_1], Union[Dict[str, Any], Direction]]
                attributes=None,            # type: Dict[str, Any]
                slo=None,                   # type: SLO
                scalingMode=AUTO_SCALE,     # type: Union[AUTO_SCALE, MANUAL_SCALE]
                routingMorphic=None,        # type: RoutingMorphic
                protectionMode=WITHOUT_PROTECTION,  # type:  Union[WITHOUT_PROTECTION, WITH_PROTECTION]
                recoveryMode=AUTO_RECOVERY, # type: Union[AUTO_RECOVERY, MANUAL_RECOVERY]
                vnfSequence=None,           # type: List[VNF]
                vnfiResourceQuota=None,     # type: Union[VNFI_RESOURCE_QUOTA_SMALL, VNFI_RESOURCE_QUOTA_LARGE]
                ):
        self.sfcUUID = sfcUUID
        self.vNFTypeSequence = vNFTypeSequence  # e.g. [FW, LB]
        self.vnfSequence = vnfSequence
        self.scalingMode = scalingMode
        self.vnfiResourceQuota = vnfiResourceQuota
        self.maxScalingInstanceNumber = maxScalingInstanceNumber
        self.protectionMode = protectionMode
        self.backupInstanceNumber = backupInstanceNumber
        self.applicationType = applicationType
        self.recoveryMode = recoveryMode
        self.routingMorphic = routingMorphic
        self.slo = slo
        if attributes is None:
            self.attributes = {}
        else:
            self.attributes = attributes  # {"zone":ZONENAME}   # TODO: MAY BE refactor to a data structure, not a dict
        self.directions = directions    # type: List[Dict[str, Any]]
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
        # TODO: MAY BE refactor direction to a data structure, not a dict

    def getSFCLength(self):
        return len(self.vNFTypeSequence)

    def getSFCTrafficDemand(self):
        return self.slo.throughput

    def getSFCLatencyBound(self):
        return self.slo.latency

    def isFixedResourceQuota(self):
        return self.vnfiResourceQuota != None

    def isAutoRecovery(self):
        # type: (None) -> bool
        return self.recoveryMode == AUTO_RECOVERY

    def isAutoScaling(self):
        # type: (None) -> bool
        return self.scalingMode == AUTO_SCALE

    def to_dict(self):
        return {
            'sfcUUID': str(self.sfcUUID),
            'vNFTypeSequence': self.vNFTypeSequence,
            'zone': self.attributes['zone'],
            'source': self.directions[0]['source'],
            'ingress': self.directions[0]['ingress'].getNodeID(),
            'match': self.directions[0]['match'],
            'egress': self.directions[0]['egress'].getNodeID(),
            'destination': self.directions[0]['destination'],
            'routingMorphic': self.routingMorphic
        }

    def __str__(self):
        string = "{0}\n".format(self.__class__)
        for key, values in self.__dict__.items():
            string = string + "{0}:{1}\n".format(key, values)
        return string

    def __repr__(self):
        return str(self)
