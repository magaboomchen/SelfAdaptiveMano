DIRECTION1_PATHID_OFFSET = 0
DIRECTION2_PATHID_OFFSET = 128

class PathSet(object):
    def __init__(self,primaryForwardingPath, backupForwardingPath):
        self.primaryForwardingPath = primaryForwardingPath # {pathID:forwardingPath}
        # {0:forwardingPath, 128:forwardingPath}
        # direction1's pathID == 0
        # direction2's pathID == 128
        self.backupForwardingPath = backupForwardingPath # {(srcID,dstID,pathID):forwardingPath}
        # direction1's pathID > 0 and < 128
        # direction2's pathID > 128 and < 256