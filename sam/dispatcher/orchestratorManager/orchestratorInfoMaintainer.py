#!/usr/bin/python
# -*- coding: UTF-8 -*-

from typing import Dict
from uuid import UUID
from sam.base.sfc import SFCI

from sam.measurement.dcnInfoBaseMaintainer import DCNInfoBaseMaintainer
from sam.orchestration.runtimeState.runtimeState import RuntimeState


class OrchestratorInfoMaintainer(object):
    def __init__(self,
                name,   # type: str
                oPid,   # type: int
                oInfoDict, # type: Dict
                dib,     # type: DCNInfoBaseMaintainer
                liveness # type: bool
            ):
        self.name = name
        self.oPid = oPid
        self.oInfoDict = oInfoDict
        self.dib = dib
        self.liveness = liveness
        self.runtimeState = RuntimeState()
        self.sfcDict = {}
        self.sfciDict = {}  # type: Dict[UUID, Dict[int, SFCI]]
        self.cpuUtilList = []
        self.memoryUtilList = []
        self.totalCPUUtilList = []
