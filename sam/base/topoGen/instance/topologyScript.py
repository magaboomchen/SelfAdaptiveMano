#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
use script to generate topology
'''

from sam.base.socketConverter import SocketConverter, BCAST_MAC
from sam.base.exceptionProcessor import *
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.topoGen.base.common import *
from sam.base.topoGen.base.mkdirs import *
from sam.base.topoGen.base.samSimulationArgParser import *
from sam.base.topoGen.instance.topology import *


if __name__ == "__main__":
    argParser = SamSimulationArgParser()
    expNum = argParser.getArgs()['e']
    topologyType = argParser.getArgs()['topo']
    podNum = argParser.getArgs()['p']
    sfcLength = argParser.getArgs()['sl']
    nPoPNum = argParser.getArgs()['nPoPNum']
    intNum = argParser.getArgs()['intNum']
    aggNum = argParser.getArgs()['aggNum']
    torNum = argParser.getArgs()['torNum']

    tg = Topology()
    if topologyType == "fat-tree":
        tg.genFatTreeTopology(expNum, podNum, nPoPNum)
    elif topologyType == "VL2":
        tg.genVL2Topology(expNum, intNum, aggNum, nPoPNum)
    elif topologyType == "testbed_sw1":
        tg.genTestbedSW1Topology(expNum, nPoPNum)
    elif topologyType == "Geant2012":
        tg.genGeantTopology(expNum, nPoPNum)
    elif topologyType == "AttMpls":
        tg.genAttMplsTopology(expNum, nPoPNum)
    elif topologyType == "SwitchL3":
        tg.genSwitchL3Topology(expNum, nPoPNum)
    elif topologyType == "Uninett2011":
        tg.genUninett2011Topology(expNum, nPoPNum)
    elif topologyType == "LogicalTwoTier":
        tg.genLogicalTwoTierTopology(expNum, aggNum, torNum, nPoPNum)
    else:
        raise ValueError("Unknown topology")
