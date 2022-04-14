#!/usr/bin/python
# -*- coding: UTF-8 -*-

import uuid

from sam.orchestration.oConfig import VNFI_ASSIGN_MODE


class VNFIIDAssigner(object):
    def __init__(self):
        self._vnfiIDPool = {}

    def _assignVNFIID(self, vnfType, serverID):
        if VNFI_ASSIGN_MODE == False:
            vnfiID = uuid.uuid1()
        elif VNFI_ASSIGN_MODE == True:
            if (vnfType, serverID) not in self._vnfiIDPool.keys():
                vnfiID = uuid.uuid1()
                self._vnfiIDPool[(vnfType, serverID)] = vnfiID
            else:
                vnfiID = self._vnfiIDPool[(vnfType, serverID)]
        else:
            raise ValueError("Unknown VNFI ASSIGN MODE {0}".format(VNFI_ASSIGN_MODE))

        return vnfiID
