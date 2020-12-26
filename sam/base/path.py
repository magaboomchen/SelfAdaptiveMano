#!/usr/bin/python
# -*- coding: UTF-8 -*-

DIRECTION1_PATHID_OFFSET = 1
DIRECTION2_PATHID_OFFSET = 128

PATHID_LENGTH = 8  # DO NOT MODIFY THIS VALUE, otherwise BESS will incurr error

# ForwardingPath is a list of paths
# Each path is a stage in SFC
# E.g. [[nodeID, nodeID,...],[]] where nodeID is switchID or serverID
# [] presenets no path and internel VNF link in the previous node
# the last nodeID in each stage distinguish P4 or Server

FRR_TYPE_UFRR = "FRR_TYPE_UFRR"
FRR_TYPE_E2EP = "FRR_TYPE_E2EP"
FRR_TYPE_NOTVIA_PSFC = "FRR_TYPE_NOTVIA_PSFC"


class ForwardingPathSet(object):
    def __init__(self, primaryForwardingPath, frrType, backupForwardingPath):
        self.primaryForwardingPath = primaryForwardingPath
        # {pathID:forwardingPath}
        # {1:forwardingPath, 128:forwardingPath}
        # direction1's pathID == 1
        # direction2's pathID == 128

        self.frrType = frrType  # UFRR, NotVia-LSFC, E2EP, None
        self.backupForwardingPath = backupForwardingPath
        # {
        #   1:{(srcID,dstID,pathID):forwardingPath},
        #   128:{(srcID,dstID,pathID):forwardingPath}
        # }
        # direction1's pathID > 1 and < 128
        # direction2's pathID > 128 and < 256

    def __str__(self):
        string = "{0}\n".format(self.__class__)
        for key,values in self.__dict__.items():
            string = string + "{0}:{1}\n".format(key, values)
        return string

    def __repr__(self):
        return str(self)
