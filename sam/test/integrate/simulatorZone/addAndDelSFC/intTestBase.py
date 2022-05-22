#!/usr/bin/python
# -*- coding: UTF-8 -*-

import time
import logging
import uuid

from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.messageAgent import SIMULATOR_ZONE
from sam.base.server import SERVER_TYPE_NFVI, Server
from sam.base.sfc import APP_TYPE_NORTHSOUTH_WEBSITE, SFC, SFCI
from sam.base.shellProcessor import ShellProcessor
from sam.base.slo import SLO
from sam.base.vnf import VNF_TYPE_MONITOR, VNF_TYPE_RATELIMITER, VNFI
from sam.orchestration.orchInfoBaseMaintainer import OrchInfoBaseMaintainer
from sam.simulator.test.testSimulatorBase import TestSimulatorBase, CLASSIFIER_DATAPATH_IP
from sam.test.testBase import APP1_REAL_IP, TestBase


class IntTestBaseClass(TestBase):
    MAXSFCIID = 0
    sfciCounter = 0
    logging.getLogger("pika").setLevel(logging.WARNING)

    def common_setup(self):
        logConfigur = LoggerConfigurator(__name__, './log',
                                            'testBaseClass.log',
                                            level='debug')
        self.logger = logConfigur.getLogger()
        self.logger.setLevel(logging.DEBUG)

        # setup
        self.sP = ShellProcessor()
        self.cleanLog()
        self.clearQueue()
        self.killAllModule()
        time.sleep(3)
        logging.info("Please start dispatcher, mediator and simulator!"\
                        " Then press Any key to continue!")
        raw_input() # type: ignore

    def getSFCFromDB(self):
        self._oib = OrchInfoBaseMaintainer("localhost", "dbAgent", "123",
                                            False)
        self.sfcInDB = self._oib.getSFC4DB(self.sfc.sfcUUID)
        return self.sfcInDB

    def genLargeBandwidthSFC(self, classifier):
        sfcUUID = uuid.uuid1()
        vNFTypeSequence = [VNF_TYPE_MONITOR, VNF_TYPE_RATELIMITER]
        maxScalingInstanceNumber = 1
        backupInstanceNumber = 0
        applicationType = APP_TYPE_NORTHSOUTH_WEBSITE
        direction1 = {
            'ID': 0,
            'source': {'node': None, 'IPv4':"*"},
            'ingress': classifier,
            'match': {'srcIP': "*",'dstIP':APP1_REAL_IP,
                'srcPort': "*",'dstPort': "*",'proto': "*"},
            'egress': classifier,
            'destination': {'node': None, 'IPv4':APP1_REAL_IP}
        }
        directions = [direction1]
        slo = SLO(latencyBound=35, throughput=0.1)
        return SFC(sfcUUID, vNFTypeSequence, maxScalingInstanceNumber,
            backupInstanceNumber, applicationType, directions,
            {'zone': SIMULATOR_ZONE}, slo=slo)

    def genSFCITemplate(self):
        vnfiSequence = None
        return SFCI(self.assignSFCIID(), vnfiSequence, None, None)
