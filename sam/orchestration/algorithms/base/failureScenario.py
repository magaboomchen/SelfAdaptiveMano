#!/usr/bin/python
# -*- coding: UTF-8 -*-


class FailureScenario(object):
    def __init__(self):
        self.elementsList = []

    def addElement(self, element):
        self.elementsList.append(element)

    def getElementsList(self):
        return self.elementsList
