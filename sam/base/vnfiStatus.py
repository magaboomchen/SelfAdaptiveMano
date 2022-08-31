#!/usr/bin/python
# -*- coding: UTF-8 -*-

import datetime
from typing import Dict, Union

from sam.base.acl import ACLTable
from sam.base.rateLimiter import RateLimiterConfig
from sam.base.monitorStatistic import MonitorStatistics
from sam.base.sfcConstant import SFC_DIRECTION_0, SFC_DIRECTION_1


class VNFIStatus(object):
    def __init__(self, inputTrafficAmount=None, # type: Dict[Union[SFC_DIRECTION_0, SFC_DIRECTION_1], int]
                 inputPacketAmount=None,        # type: Dict[Union[SFC_DIRECTION_0, SFC_DIRECTION_1], int]
                 outputTrafficAmount=None,      # type: Dict[Union[SFC_DIRECTION_0, SFC_DIRECTION_1], int]
                 outputPacketAmount=None,       # type: Dict[Union[SFC_DIRECTION_0, SFC_DIRECTION_1], int]
                 state=None                    # type: Union[MonitorStatistics, RateLimiterConfig, ACLTable]
                ):
        self.inputTrafficAmount = inputTrafficAmount  # Dict[int, int]
        self.inputPacketAmount = inputPacketAmount
        self.outputTrafficAmount = outputTrafficAmount
        self.outputPacketAmount = outputPacketAmount
        self.state = state
        self.timestamp = datetime.datetime.now()

    def __str__(self):
        string = "{0}\n".format(self.__class__)
        for key, values in self.__dict__.items():
            string = string + "{0}:{1}\n".format(key, values)
        return string
