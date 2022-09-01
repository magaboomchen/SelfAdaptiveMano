#!/usr/bin/python
# -*- coding: UTF-8 -*-


from typing import Any, Dict, List, Union
from uuid import uuid1

from sam.base.sfc import SFC, SFCI
from sam.base.link import Link
from sam.base.vnf import VNFI
from sam.base.flow import Flow
from sam.base.switch import Switch
from sam.base.server import Server
from sam.base.messageAgent import SIMULATOR_ZONE, TURBONET_ZONE
from sam.measurement.dcnInfoBaseMaintainer import DCNInfoBaseMaintainer

ATTR_ZONE = "zone"
ATTR_SFC = "sfc"
ATTR_SFCUUID = "sfcUUID"
ATTR_SFCI = "sfci"
ATTR_CLASSIFIER = "classifier"
ATTR_ERROR = "error"
ATTR_SOURCE = "source"
ATTR_DIB = "dib"
ATTR_MAPPING_TYPE = "mappingType"

ATTR_SERVERS = "servers"
ATTR_SWITCHES = "switches"
ATTR_LINK = "links"
ATTR_VNFIS = "vnfis"
ATTR_FLOWS = "flows"

ATTR_SERVER_DOWN = "serverDown"
ATTR_SERVER_UP = "serverUp"

ATTR_VNFIS_STATE_DICT = "vnfisStateDict"
ATTR_SFCIS_DICT = "sfcisDict"
ATTR_ALL_ZONE_DETECTION_DICT = "allZoneDetectionDict"
ATTR_DETECTION_DICT = "detectionDict"


class Attributes(object):
    def __init__(self, zone=None,    # type: str
                sfc=None,            # type: SFC
                sfcUUID=None,        # type: uuid1
                sfci=None,           # type: SFCI
                classifier=None,     # type: Union[Server, Switch]
                error=None,          # type: str
                source=None,         # type: str
                dib=None,            # type: DCNInfoBaseMaintainer
                mappingType=None,    # type: str
                servers=None,        # type: Dict[int, Dict[str, Union[Server, bool]]]
                switches=None,       # type: Dict[int, Dict[str, Union[Switch, bool]]]
                links=None,          # type: Dict[int, Dict[str, Union[Link, bool]]]
                vnfis=None,          # type: Dict[int, Dict[str, Union[VNFI, bool]]]
                flows=None,          # type: Flow
                serverDown=None,     # type: List[Server]
                serverUp=None,       # type: List[Server]
                vnfisStateDict=None, # type: Dict[uuid1, Dict[str, Any]]
                sfcisDict=None,      # type: Dict[uuid1, Dict[str, Any]]
                allZoneDetectionDict=None,   # type: Dict[Union[SIMULATOR_ZONE, TURBONET_ZONE], Dict[str, Any]]
                detectionDict=None   # type: Dict[str, Any]
            ):
        self.zone = zone
        self.sfc = sfc
        self.sfcUUID = sfcUUID
        self.sfci = sfci
        self.classifier = classifier
        self.error = error
        self.source = source
        self.dib = dib
        self.mappingType = mappingType

        self.servers = servers
        self.switches = switches
        self.links = links
        self.vnfis = vnfis
        self.flows = flows

        self.serverDown = serverDown
        self.serverUp = serverUp

        self.vnfisStateDict = vnfisStateDict
        self.sfcisDict = sfcisDict
        self.allZoneDetectionDict = allZoneDetectionDict
        self.detectionDict = detectionDict

    def toDict(self):
        return dict(
            (key, value)
            for (key, value) in self.__dict__.items()
            if value != None
            )

    def fromDict(self, dictionary):
        for key in list(self.__dict__.keys()):
            if key in dictionary:
                self.__dict__[key] = dictionary[key]
