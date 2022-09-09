#!/usr/bin/python
# -*- coding: UTF-8 -*-


class RuntimeState(object):
    def __init__(self):
        self.disconnection = False
        self.classifierUnavailable = False
        self.resourceExceedWateLine = False

    def setDisconnectionState(self, state):
        # type: (bool) -> None
        self.disconnection = state

    def setClassifierUnavailableState(self, state):
        # type: (bool) -> None
        self.classifierUnavailable = state

    def setResourceExceedWateLineState(self, state):
        # type: (bool) -> None
        self.resourceExceedWateLine = state

    def isValidRuntimeState(self):
        return self.disconnection == False \
                and self.classifierUnavailable == False \
                and self.resourceExceedWateLine == False

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)
