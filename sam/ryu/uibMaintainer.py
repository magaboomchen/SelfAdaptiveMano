from sam.base.xibMaintainer import *

# TODO

class UIBMaintainer(XInfoBaseMaintainer):
    def __init__(self, *args, **kwargs):
        super(UIBMaintainer, self).__init__(*args, **kwargs)
        self.groupIDSets = {}
        self.sfciRIB = {}

    def assignGroupID(self,dpid):
        if not self.groupIDSets.has_key(dpid):
            self.groupIDSets[dpid] = [0]
            return 0
        else:
            groupID = self.genAvailableMiniNum4List(self.groupIDSets[dpid])
            self.groupIDSets[dpid].append(groupID)
            return groupID

    def delGroupID(self,dpid,groupID):
        self.groupIDSets[dpid].remove(groupID)

    def addFlowTableEntry(self,SFCIID,dpid,matchFields,groupID=None):
        if not self.sfciRIB.has_key(SFCIID):
            self.sfciRIB[SFCIID] = {}
        if not self.sfciRIB[SFCIID].has_key(dpid):
            self.sfciRIB[SFCIID][dpid] = []
        if groupID == None:
            self.sfciRIB[SFCIID][dpid].append(
                {"match":matchFields})
        else:
            self.sfciRIB[SFCIID][dpid].append(
                {"match":matchFields,"groupID":groupID})

    def delSFCIFlowTableEntry(self,SFCIID):
        del self.sfciRIB[SFCIID]
    
    def getSFCIFlowTableEntry(self,SFCIID,dpid):
        return self.sfciRIB[SFCIID][dpid]