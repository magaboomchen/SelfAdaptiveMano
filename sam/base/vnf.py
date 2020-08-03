VNF_TYPE_FW = 1
VNF_TYPE_IDS = 2
VNF_TYPE_MONITOR = 3
VNF_TYPE_LB = 4
VNF_TYPE_TRAFFICSHAPER = 5

class VNFIStatus(object):
    def __init__(self):
        self.inputTrafficAmount = None
        self.inputPacketAmount = None
        self.outputTrafficAmount = None
        self.outputPacketAmount = None

class VNFI(object):
    def __init__(self, VNFID=None,VNFType=None,VNFIID=None,config=None,server=None,vnfiStatus=None):
        self.VNFID = VNFID
        self.VNFType = VNFType
        self.VNFIID = VNFIID
        self.config = config
        self.server = server
        self.vnfiStatus = vnfiStatus

class VNFIRequest(object):
    def __init__(self, userID, requestID, requestType, VNFIID, config=None):
        self.userID =  userID # 0 is root
        self.requestID = requestID # uuid1()
        self.requestType = requestType # GETCONFIG/UPDATECONFIG/GETVNFI
        self.VNFIID = VNFIID
        self.config = config