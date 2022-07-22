#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.compatibility import SAM_MODULE_ABS_PATH
from sam.base.messageAgent import SIMULATOR_ZONE, TURBONET_ZONE


NFV_ALLOCATION_PERCENTAGE_IN_SIMULATOR_ZONE = 0.25
NFV_ALLOCATION_PERCENTAGE_IN_EMULATOR_ZONE = 0.25

TIME_BUDGET = 25
AUTO_SCALE = False

CONSTANT_ORCHESTRATOR_NUM = 32
RE_INIT_TABLE = True    # Please disable this when presenting after clean up all mysql data.


ZONE_INFO_LIST = [
    {
        "zone": SIMULATOR_ZONE,
        "info":{
            "topoType": "fat-tree",
            "podNum":32,
            "topoFilePath": "{0}/base/topoGen/instance/topology/fat-tree/0/fat-tree-k=32_V=512_M=100.M=100.pickle".format(SAM_MODULE_ABS_PATH)
        }
    },
    {
        "zone": TURBONET_ZONE,
        "info":{
            "topoType": "fat-tree",
            "podNum":4,
            "topoFilePath": "{0}/base/topoGen/instance/topology/fat-tree/0/fat-tree-k=4_V=2_M=100.M=100.pickle".format(SAM_MODULE_ABS_PATH)
        }
    }
]
