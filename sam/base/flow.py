#!/usr/bin/python
# -*- coding: UTF-8 -*-


class Flow(object):
    def __init__(self, identifier):
        self.identifier = identifier
        self.advantagePointList = []    # advantage points which measured this flow, e.g. switchID

    def __str__(self):
        string = "{0}\n".format(self.__class__)
        for key,values in self.__dict__.items():
            string = string + "{0}:{1}\n".format(key, values)
        return string

    def __repr__(self):
        return str(self)
