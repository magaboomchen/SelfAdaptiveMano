#!/usr/bin/python
# -*- coding: UTF-8 -*-

import docker

from sam.base.vnf import *

# vnfi states
VNFI_STATE_PROCESSING = 'VNFI_STATE_PROCESSING'
VNFI_STATE_DEPLOYED = 'VNFI_STATE_DEPLOYED'
VNFI_STATE_FAILED = 'VNFI_STATE_FAILED'

class VNFIDeployStatus(object):
    def __init__(self, vnfi, state):
        self.vnfi = vnfi
        self.state = state
        self.containerID = None 
        self.vioStart = None  # start port of virtio in dpdk vdev
        self.error = None # error of the docker

class VNFIMaintainer(object):
    def __init__(self):
        self._vnfiSet = {}   # {sfciID: {vnfiID: VNFIDeployStatus}}
     
    def addSFCI(self, sfciID):
        self._vnfiSet[sfciID] = {}
    
    def addVNFI(self, sfciID, vnfi):
        self._vnfiSet[sfciID][vnfi.VNFIID] = VNFIDeployStatus(vnfi, VNFI_STATE_PROCESSING)

    def setVNFIState(self, sfciID, vnfi, state):
        self._vnfiSet[sfciID][vnfi.VNFIID].state = state 

    def setVNFIContainerID(self, sfciID, vnfi, containerID):
        self._vnfiSet[sfciID][vnfi.VNFIID].containerID = containerID

    def setVNFIVIOStart(self, sfciID, vnfi, vioStart):
        self._vnfiSet[sfciID][vnfi.VNFIID].vioStart = vioStart

    def setVNFIError(self, sfciID, vnfi, error):
        self._vnfiSet[sfciID][vnfi.VNFIID].error = error

    def getVNFIDeployStatus(self, sfciID, vnfi):
        return self._vnfiSet[sfciID][vnfi.VNFIID]
    
    def getSFCI(self, sfciID):
        return self._vnfiSet[sfciID]