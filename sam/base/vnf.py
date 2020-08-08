VNF_TYPE_FORWARD = 1
VNF_TYPE_FW = 2
VNF_TYPE_IDS = 3
VNF_TYPE_MONITOR = 4
VNF_TYPE_LB = 5
VNF_TYPE_TRAFFICSHAPER = 6

class VNFIStatus(object):
    def __init__(self):
        self.inputTrafficAmount = None
        self.inputPacketAmount = None
        self.outputTrafficAmount = None
        self.outputPacketAmount = None

class VNFI(object):
    def __init__(self, VNFID=None,VNFType=None,VNFIID=None,config=None,node=None,vnfiStatus=None):
        self.VNFID = VNFID
        self.VNFType = VNFType
        self.VNFIID = VNFIID
        self.config = config
        self.node = node    # server or switch
        self.vnfiStatus = vnfiStatus

class VNFIRequest(object):
    def __init__(self, userID, requestID, requestType, VNFIID, config=None):
        self.userID =  userID # 0 is root
        self.requestID = requestID # uuid1()
        self.requestType = requestType # GETCONFIG/UPDATECONFIG/GETVNFI
        self.VNFIID = VNFIID
        self.config = config