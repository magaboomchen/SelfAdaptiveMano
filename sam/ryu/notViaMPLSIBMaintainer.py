#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.ryu.uibMaintainer import UIBMaintainer

# TODO: test

OVS_MPLSLabel_OFFSET = 0


class NotViaMPLSIBMaintainer(UIBMaintainer):
    def __init__(self, *args, **kwargs):
        super(NotViaMPLSIBMaintainer, self).__init__(*args, **kwargs)
        self.groupIDSets = {}
        self.sfciRIB = {}
        self.mplsLabelList = []
        self.labelAndSFCIMapping = {}

    def assignMPLSLabel(self, sfciID, pathID):
        newMPLSLabel = self.genAvailableMiniNum4List(self.mplsLabelList)
        self.mplsLabelList.append(newMPLSLabel)
        self.labelAndSFCIMapping[(sfciID,pathID)] = newMPLSLabel
        return newMPLSLabel + OVS_MPLSLabel_OFFSET

    def getMPLSLabel(self, sfciID, pathID):
        if self.labelAndSFCIMapping.has_key((sfciID,pathID)):
            return self.labelAndSFCIMapping[(sfciID,pathID)] + OVS_MPLSLabel_OFFSET
        return None

    def delMPLSLabel(self, sfciID, pathID):
        mplsLabel = self.labelAndSFCIMapping[(sfciID,pathID)]
        del self.labelAndSFCIMapping[(sfciID,pathID)]
        self.mplsLabelList.remove(mplsLabel)
