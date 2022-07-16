#!/usr/bin/python
# -*- coding: UTF-8 -*-

import pprint

from sam.base.server import Server
from sam.base.vnf import VNFIStatus
from sam.serverController.bess.bess import BESS
from sam.serverController.bess import protobuf_to_dict as pb_conv
from sam.serverController.bessControlPlane import BessControlPlane


class SFFMonitor(BessControlPlane):
    def __init__(self, sibms, logger):
        self.sibms = sibms
        self.logger = logger

    def monitorSFCIHandler(self):
        sfcisDict = self.sibms.getAllSFCIs()
        for sfciID, sfci in sfcisDict.items():
            vnfiSequence = sfci.vnfiSequence
            for vnfis in vnfiSequence:
                for vnfi in vnfis:
                    if type(vnfi.node) == Server:
                        vnfiStatus = self._getTrafficStatusOfVNFI(vnfi)
                        vnfi.vnfiStatus = vnfiStatus

        resDict = {"sfcisDict":sfcisDict}
        return resDict

    def _getTrafficStatusOfVNFI(self, vnfi):
        vnfiID = vnfi.vnfiID
        server = vnfi.node
        serverID = server.getServerID()
        sibm = self.sibms.getSibm(serverID)
        serverControlIP = server.getControlNICIP()
        bessServerUrl = serverControlIP + ":10514"
        client = BESS()
        client.connect(grpc_url=bessServerUrl)

        vnfPMDPort0Name = sibm.getModuleName("PMDPort",vnfiID,0)
        response = client.get_port_stats(vnfPMDPort0Name)
        assert 0 == response.error.code
        self.logger.warning("direction1 pmdport")
        port0res = pb_conv.protobuf_to_dict(response)

        vnfPMDPort1Name = sibm.getModuleName("PMDPort",vnfiID,1)
        response = client.get_port_stats(vnfPMDPort1Name)
        assert 0 == response.error.code
        self.logger.warning("direction1 pmdport")
        port1res = pb_conv.protobuf_to_dict(response)
        # port0res, port1res
        # {'inc': {'actual_hist': [111],
        #         'bytes': 89,
        #         'diff_hist': [111],
        #         'packets': 1,
        #         'requested_hist': [111]},
        # 'out': {'actual_hist': [111],
        #         'bytes': 89,
        #         'diff_hist': [111],
        #         'packets': 1,
        #         'requested_hist': [111]},
        # 'timestamp': 1658036988.432575
        # }

        vnfiStatus = VNFIStatus(
            inputTrafficAmount={
                "Direction1":port0res['inc']['bytes'],
                "Direction2":port1res['inc']['bytes']
            },
            inputPacketAmount={
                "Direction1":port0res['inc']['packets'],
                "Direction2":port1res['inc']['packets']
            },
            outputTrafficAmount={
                "Direction1":port0res['out']['bytes'],
                "Direction2":port1res['out']['bytes']
            },
            outputPacketAmount={
                "Direction1":port0res['out']['packets'],
                "Direction2":port1res['out']['packets']
            }
        )
        return vnfiStatus
