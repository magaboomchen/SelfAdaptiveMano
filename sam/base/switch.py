#!/usr/bin/python
# -*- coding: UTF-8 -*-

SWITCH_TYPE_TOR = "SWITCH_TYPE_TOR"
SWITCH_TYPE_DCNGATEWAY = "SWITCH_TYPE_DCNGATEWAY"


class Switch(object):
    def __init__(self, switchID, switchType, lanNet=None, programmable=False):
        self.switchID = switchID
        self.switchType = switchType
        self.lanNet = lanNet
        self.programmable = programmable

    def __str__(self):
        string = "{0}\n".format(self.__class__)
        for key,values in self.__dict__.items():
            string = string + "{0}:{1}\n".format(key, values)
        return string

    def __repr__(self):
        return str(self)
