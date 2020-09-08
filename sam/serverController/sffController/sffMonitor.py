#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.serverController.bessControlPlane import *

class SFFMonitor(BessControlPlane):
    def __init__(self,sibms):
        self.sibms = sibms