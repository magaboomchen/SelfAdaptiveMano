#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.ryu.ribMaintainerBase import RIBMaintainerBase

# TODO: test

OVS_VLANID_OFFSET = 4096

class NotViaVLANIBMaintainer(RIBMaintainerBase):
    def __init__(self, *args, **kwargs):
        super(NotViaVLANIBMaintainer, self).__init__(*args, **kwargs)
        self.groupIDSets = {}
        self.sfciRIB = {}
        self.vlanIDs = []
        self.vlanIDSFCIMapping = {}
    
    def assignVLANID(self, sfciID, pathID):
        newVLANID = self.genAvailableMiniNum4List(self.vlanIDs)
        self.vlanIDs.append(newVLANID)
        self.vlanIDSFCIMapping[(sfciID,pathID)] = newVLANID
        return newVLANID + OVS_VLANID_OFFSET

    def getVLANID(self, sfciID, pathID):
        if self.vlanIDSFCIMapping.has_key((sfciID,pathID)):
            return self.vlanIDSFCIMapping[(sfciID,pathID)] + OVS_VLANID_OFFSET
        return None

    def delVLANID(self, sfciID, pathID):
        vlanID = self.vlanIDSFCIMapping[(sfciID,pathID)]
        del self.vlanIDSFCIMapping[(sfciID,pathID)]
        self.vlanIDs.remove(vlanID)
