#!/usr/bin/python
# -*- coding: UTF-8 -*-

SWITCH_TYPE_FORWARD = "SWITCH_TYPE_FORWARD" # this switch only connect other switch or classifer
SWITCH_TYPE_NPOP = "SWITCH_TYPE_NPOP" # those servers connecting this switch can provide VNF
SWITCH_TYPE_DCNGATEWAY = "SWITCH_TYPE_DCNGATEWAY"   # datacenter gateway

SWITCH_DEFAULT_TCAM_SIZE = 2000


class Switch(object):
    def __init__(self, switchID, switchType, lanNet=None, programmable=False,
                    tcamSize=SWITCH_DEFAULT_TCAM_SIZE, tcamUsage=0):
        self.switchID = switchID    # unique id in network
        self.switchType = switchType
        self.lanNet = lanNet    # the IP net address of this switches. All servers connecting this switches are in this IP net address
        self.programmable = programmable    # bool type, '1' if this switch is a P4 switch
        self.tcamSize = tcamSize
        self.tcamUsage = tcamUsage
        self._coreUtilization = []
        self.supportNF = [] # switch itself can support NFs
        self.supportVNF = []    # connected servers support VNFs
        self.gatewayPortLists = []  # e.g. [0]

    def __str__(self):
        string = "{0}\n".format(self.__class__)
        for key,values in self.__dict__.items():
            string = string + "{0}:{1}\n".format(key, values)
        return string

    def __repr__(self):
        return str(self)
