from slo import *
from vnf import *

SFCR_STATE_INITIAL = "SFCR_STATE_INITIAL"
SFCR_STATE_IN_PROCESSING = "SFCR_STATE_IN_PROCESSING"
SFCR_STATE_SUCCESSFUL = "SFCR_STATE_SUCCESSFUL"
SFCR_STATE_FAILED = "SFCR_STATE_FAILED"
SFCR_STATE_IN_ADAPTIVE = "SFCR_STATE_IN_ADAPTIVE"

APP_TYPE_NORTHSOUTH_WEBSITE = "APP_TYPE_NORTHSOUTH_WEBSITE"

class SFCI(object):
    def __init__(self, SFCIID, VNFISequence, sloRealTimeValue=None,
        pathSet=None):
        self.SFCIID = SFCIID
        self.VNFISequence = VNFISequence    # only show the direction1
        self.sloRealTimeValue = sloRealTimeValue
        self.pathSet = pathSet

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

        # [
        # {
        # 'ID': 0   # forwarding direction
        # 'source' : Outside
        # 'ingress': Any # SAM will find the nearest classifier and configure switch to direct traffic to this classifier
        # 'match': {srcIP, dstIP, srcPort, dstPort, proto} # classifier's match
        # 'egress' : Any # defualt is the classifier under the tor of destination
        # 'destination': websiteIP
        # },
        # {
        # 'ID': 1   # reverse direction
        # 'source' : WEBSITE
        # 'ingress': Any # SAM will find the nearest classifier and configure switch to direct traffic to this classifier
        # 'match': {srcIP, dstIP, srcPort, dstPort, proto} # classifier's match
        # 'egress': Any # defualt is the classifier under the tor of destination
        # 'destination': Any # defualt is DCNGATEAWAY
        # }
        # ]

        # following member is created by orchestrator
        self.sFCIs = sFCIs # {SFCIID:active, SFCIID:active}, For switch, we use pathID to distinguish different direction; For bess, we use (src,dst) pair to distinguish different direction.

class SFCRequest(object):
    def __init__(self, userID, requestID, requestType,
        requestState=SFCR_STATE_INITIAL, sfc=None, objRequestID=None, sla=None,
        traffic=None):
        self.userID =  userID # 0 is root
        self.requestID = requestID # uuid1()
        self.requestType = requestType # CREATE_SFC_REQUEST/DELETE_SFC_REQUEST/GET_SFC_REQUEST/GETALL_SFC_REQUEST/ADDSFCINST/DELETESFCINST
        self.requestState = requestState # SFCR_STATE_INITIAL, SFCR_STATE_IN_PROCESSING, SFCR_STATE_SUCCESSFUL, SFCR_STATE_FAILED, SFCR_STATE_IN_ADAPTIVE
        self.objRequestID = objRequestID    # default: None
        self.sfc = sfc
        self.traffic = traffic