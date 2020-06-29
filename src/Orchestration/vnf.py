VNF_TYPE_FW = 1
VNF_TYPE_IDS = 2
VNF_TYPE_NAT = 3
VNF_TYPE_LB = 4

class VNF():
    def __init__(self, attrDict):
        self.VNFID = attrDict["VNFID"]
        self.VNFType = attrDict["VNFType"]
        self.VNFUUID = attrDict["VNFUUID"]
        self.config = attrDict["config"]
        self.serverMAC = attrDict["serverMAC"]
        self.serverPrimaryIP = attrDict["serverPrimaryIP"]
        self.serverIP = attrDict["serverIP"]