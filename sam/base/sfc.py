from sam.base.slo import *
from sam.base.vnf import *

SFC_DOMAIN_PREFIX = "10.0.0.0"
SFC_DOMAIN_PREFIX_LENGTH = 8    # DO NOT MODIFY THIS VALUE,
    # otherwise BESS will incurr error
SFCID_LENGTH = 12  # DO NOT MODIFY THIS VALUE, otherwise BESS will incurr error

SFCR_STATE_INITIAL = "SFCR_STATE_INITIAL"
SFCR_STATE_IN_PROCESSING = "SFCR_STATE_IN_PROCESSING"
SFCR_STATE_SUCCESSFUL = "SFCR_STATE_SUCCESSFUL"
SFCR_STATE_FAILED = "SFCR_STATE_FAILED"
SFCR_STATE_IN_ADAPTIVE = "SFCR_STATE_IN_ADAPTIVE"

APP_TYPE_NORTHSOUTH_WEBSITE = "APP_TYPE_NORTHSOUTH_WEBSITE"


class SFCI(object):
    def __init__(self, SFCIID, VNFISequence, sloRealTimeValue=None,
        ForwardingPathSet=None):
        self.SFCIID = SFCIID
        self.VNFISequence = VNFISequence    # only show the direction1
        self.sloRealTimeValue = sloRealTimeValue
        self.ForwardingPathSet = ForwardingPathSet


class SFC(object):
    def __init__(self, sfcUUID, vNFTypeSequence, maxScalingInstanceNumber,
        backupInstanceNumber, applicationType, directions=None,
        sFCIs=[], traffic=None, slo=None, sloRealTimeValue=None):
        self.sfcUUID = sfcUUID
        self.vNFTypeSequence = vNFTypeSequence # [FW, LB]
        self.maxScalingInstanceNumber = maxScalingInstanceNumber # 2
        self.backupInstanceNumber = backupInstanceNumber # 1
        self.applicationType = applicationType # NORTHSOUTH_WEBSITE
        self.slo = slo
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


class SFCRequest(object):
    def __init__(self, userID, requestID, requestType,
        requestState=SFCR_STATE_INITIAL, sfc=None, objRequestID=None,
        sla=None, traffic=None):
        self.userID =  userID # 0 is root
        self.requestID = requestID # uuid1()
        self.requestType = requestType
        self.requestState = requestState 
        self.objRequestID = objRequestID # default: None
        self.sfc = sfc
        self.traffic = traffic
