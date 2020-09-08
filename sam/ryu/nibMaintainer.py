#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.ryu.uibMaintainer import UIBMaintainer

# TODO: test

OVS_VLANID_OFFSET = 4096

class NIBMaintainer(UIBMaintainer):
    def __init__(self, *args, **kwargs):
        super(NIBMaintainer, self).__init__(*args, **kwargs)
        self.groupIDSets = {}
        self.sfciRIB = {}
        self.vlanIDs = []
        self.vlanIDSFCIMapping = {}
    
    def assignVLANID(self, SFCIID, pathID):
        newVLANID = self.genAvailableMiniNum4List(self.vlanIDs)
        self.vlanIDs.append(newVLANID)
        self.vlanIDSFCIMapping[(SFCIID,pathID)] = newVLANID
        return newVLANID + OVS_VLANID_OFFSET

    def getVLANID(self, SFCIID, pathID):
        if self.vlanIDSFCIMapping.has_key((SFCIID,pathID)):
            return self.vlanIDSFCIMapping[(SFCIID,pathID)] + OVS_VLANID_OFFSET
        return None

    def delVLANID(self, SFCIID, pathID):
        vlanID = self.vlanIDSFCIMapping[(SFCIID,pathID)]
        del self.vlanIDSFCIMapping[(SFCIID,pathID)]
        self.vlanIDs.remove(vlanID)
