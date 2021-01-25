#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.link import *
from sam.base.server import *
from sam.base.switch import *


class FailureScenario(object):
    def __init__(self):
        self.elementsList = []
        self.elementIDList = []

    def addElement(self, element):
        self.elementsList.append(element)

    def getElementsList(self):
        return self.elementsList

    def getFailureElementsIDInList(self):
        # nodeIDList = []
        # for node in self.elementsList:
        #     if type(node) == Server:
        #         nodeID = node.getServerID()
        #     elif type(node) == Switch:
        #         nodeID = node.switchID
        #     else:
        #         raise ValueError("Unknown element type:{0}".format(
        #             type(node)))
        #     nodeIDList.append(nodeID)
        # return nodeIDList

        elementIDList = []
        for element in self.elementsList:
            if type(element) == Server:
                elementID = element.getServerID()
            elif type(element) == Switch:
                elementID = element.switchID
            elif type(element) == Link:
                elementID = (element.srcID, element.dstID)
            else:
                raise ValueError("Unknown element type:{0}".format(
                    type(element)))
            elementIDList.append(elementID)
        return elementIDList
