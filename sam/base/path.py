DIRECTION1_PATHID_OFFSET = 0
DIRECTION2_PATHID_OFFSET = 128

# ForwardingPath is a list of paths
# Each path is a stage in SFC
# E.g. [[nodeID, nodeID,...],[]] where nodeID is switchID or serverID
# [] presenets no path and internel VNF link in the previous node
# the last nodeID in each stage distinguish P4 or Server

class ForwardingPathSet(object):
    def __init__(self,primaryForwardingPath, frrType, backupForwardingPath):
        self.primaryForwardingPath = primaryForwardingPath # {pathID:forwardingPath}

        # {0:forwardingPath, 128:forwardingPath}
        # direction1's pathID == 0
        # direction2's pathID == 128
        self.frrType = frrType  # UFFR, NotVia
        self.backupForwardingPath = backupForwardingPath # {(srcID,dstID,pathID):forwardingPath}
        # direction1's pathID > 0 and < 128
        # direction2's pathID > 128 and < 256