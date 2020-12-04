#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.serverController.bessControlPlane import *


class SFFMonitor(BessControlPlane):
    def __init__(self,sibms,logger):
        self.sibms = sibms
        self.logger = logger