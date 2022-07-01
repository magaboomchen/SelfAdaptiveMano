#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.messageAgent import SIMULATOR_ZONE, TURBONET_ZONE


NFV_ALLOCATION_PERCENTAGE_IN_SIMULATOR_ZONE = 0.25
NFV_ALLOCATION_PERCENTAGE_IN_EMULATOR_ZONE = 0.25

TIME_BUDGET = 25
AUTO_SCALE = False

CONSTANT_ORCHESTRATOR_NUM = 4

ZONE_INFO_LIST = [
    {
        "zone": SIMULATOR_ZONE,
        "info":{
            "topoType": "fat-tree",
            "podNum":32,
            "topoFilePath": "/home/smith/Projects/SelfAdaptiveMano/sam/base/topoGen/instance/topology/fat-tree/0/fat-tree-k=32_V=512_M=100.M=100.pickle"
        }
    },
    {
        "zone": TURBONET_ZONE,
        "info":{
            "topoType": "fat-tree",
            "podNum":4,
            "topoFilePath": "/home/smith/Projects/SelfAdaptiveMano/sam/base/topoGen/instance/topology/fat-tree/0/fat-tree-k=4_V=2_M=100.M=100.pickle"
        }
    }
]
