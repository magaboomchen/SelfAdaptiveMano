#!/usr/bin/python
# -*- coding: UTF-8 -*-

from typing import Union

DIRECTION0_PATHID_OFFSET = 1
DIRECTION1_PATHID_OFFSET = 128

PATHID_LENGTH = 8  # DO NOT MODIFY THIS VALUE, otherwise BESS will incurr error

# ForwardingPath is a list of paths
# Each path is a stage in SFC
# E.g. [[nodeID, nodeID,...],[]] where nodeID is switchID or serverID
# [] presenets no path and internel VNF link in the previous node
# the last nodeID in each stage distinguish P4 or Server

MAPPING_TYPE_NONE = "MAPPING_TYPE_NONE"
MAPPING_TYPE_UFRR = "MAPPING_TYPE_UFRR"
MAPPING_TYPE_MMLPSFC = "MAPPING_TYPE_MMLPSFC"
MAPPING_TYPE_E2EP = "MAPPING_TYPE_E2EP"
MAPPING_TYPE_NOTVIA = "MAPPING_TYPE_NOTVIA"
MAPPING_TYPE_NOTVIA_PSFC = "MAPPING_TYPE_NOTVIA_PSFC"
MAPPING_TYPE_INTERFERENCE = "MAPPING_TYPE_INTERFERENCE"
MAPPING_TYPE_SHORTEST_PATH = "MAPPING_TYPE_SHORTEST_PATH"
MAPPING_TYPE_NETPACK = "MAPPING_TYPE_NETPACK"
MAPPING_TYPE_NETSOLVER_ILP = "MAPPING_TYPE_NETSOLVER_ILP"


class ForwardingPathSet(object):
    def __init__(self, primaryForwardingPath,
                mappingType, backupForwardingPath):
        self.primaryForwardingPath = primaryForwardingPath  # type: dict[Union[DIRECTION0_PATHID_OFFSET, DIRECTION1_PATHID_OFFSET], list(tuple[int, int])]
        # direction0's pathID is DIRECTION0_PATHID_OFFSET
        # direction1's pathID is DIRECTION1_PATHID_OFFSET
        # {
        #   DIRECTION0_PATHID_OFFSET: forwardingPath,
        #   DIRECTION1_PATHID_OFFSET: forwardingPath
        # }

        self.mappingType = mappingType  # MAPPING_TYPE_NONE, MAPPING_TYPE_UFRR, etc
        self.backupForwardingPath = backupForwardingPath
        # {
        #   1:{(srcID,dstID,pathID):forwardingPath},
        #   128:{(srcID,dstID,pathID):forwardingPath}
        # }
        # direction0's pathID > 1 and < 128
        # direction1's pathID > 128 and < 256

    def __str__(self):
        string = "{0}\n".format(self.__class__)
        for key,values in self.__dict__.items():
            string = string + "{0}:{1}\n".format(key, values)
        return string

    def __repr__(self):
        return str(self)
