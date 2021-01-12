#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
store dcn information
e.g. switch, server, link, sfc, sfci, vnfi
'''

import uuid

from sam.base.xibMaintainer import XInfoBaseMaintainer


class SimulatorInfoBaseMaintainer(XInfoBaseMaintainer):
    def __init__(self):
        super(SimulatorInfoBaseMaintainer, self).__init__()
        pass

    def addSwitch(self, switch):
        pass
