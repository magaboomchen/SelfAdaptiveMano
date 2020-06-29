class UsrSFCList():
    def __init__(self,usrSFCID):
        self.usrSFCID = usrSFCID
        self.SFCList = []

    def addSFC(self,sfc):
        self.SFCList.append(sfc)

    def delSFC(self,sfc):
        self.SFCList.remove(sfc)

class SFC():
    def __init__(self, attrDict):
        self.SFCID = attrDict["SFCID"]  # SFCID: int
        self.VNFISeq = attrDict["VNFISeq"]  # VNFISeq: a list, e.g. [[vnf1-1,vnf1-2],[vnf2-1,vnf2-2],[vnf3-1,vnf3-2]]