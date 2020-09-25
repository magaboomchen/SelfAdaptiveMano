#!/usr/bin/python
# -*- coding: UTF-8 -*-


class Link(object):
    def __init__(self, srcID, dstID):
        self.srcID = srcID
        self.dstID = dstID

    def __str__(self):
        string = "{0}\n".format(self.__class__)
        for key,values in self.__dict__.items():
            string = string + "{0}:{1}\n".format(key, values)
        return string

    def __repr__(self):
        return str(self)

