#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.vnf import VNFI
from sam.base.server import Server
from sam.base.vnfiStatus import VNFIStatus
from sam.serverController.bess.bess import BESS
from sam.base.sfcConstant import SFC_DIRECTION_0, SFC_DIRECTION_1
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
        # type: (VNFI) -> VNFIStatus
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
        self.logger.warning("direction0 pmdport")
        port0res = pb_conv.protobuf_to_dict(response)

        vnfPMDPort1Name = sibm.getModuleName("PMDPort",vnfiID,1)
        response = client.get_port_stats(vnfPMDPort1Name)
        assert 0 == response.error.code
        self.logger.warning("direction1 pmdport")
        port1res = pb_conv.protobuf_to_dict(response)

        # self.logger.debug("port res {0}".format(port1res))

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

        # {
        #     'inc': {
        #         'requested_hist': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 37433967],
        #         'actual_hist': [37433967, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], 
        #         'diff_hist': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 37433967]
        #     }, 
        #     'out': {
        #         'requested_hist': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], 
        #         'actual_hist': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], 
        #         'diff_hist': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        #     },
        #     'timestamp': 1661347872.187717
        # }

        port0res = self._preProcessPortRes(port0res)
        port1res = self._preProcessPortRes(port1res)

        inputTrafficAmount = {
                                SFC_DIRECTION_0:port0res['inc']['bytes'],
                                SFC_DIRECTION_1:port1res['inc']['bytes']
                            }
        inputPacketAmount = {
                                SFC_DIRECTION_0:port0res['inc']['packets'],
                                SFC_DIRECTION_1:port1res['inc']['packets']
                            }
        outputTrafficAmount = {
                                SFC_DIRECTION_0:port0res['out']['bytes'],
                                SFC_DIRECTION_1:port1res['out']['bytes']
                            }
        outputPacketAmount = {
                                SFC_DIRECTION_0:port0res['out']['packets'],
                                SFC_DIRECTION_1:port1res['out']['packets']
                            }

        vnfiStatus = VNFIStatus(
            inputTrafficAmount=inputTrafficAmount,
            inputPacketAmount=inputPacketAmount,
            outputTrafficAmount=outputTrafficAmount,
            outputPacketAmount=outputPacketAmount
        )
        return vnfiStatus

    def _preProcessPortRes(self, portRes):
        zeroTraffic = False
        for key in ['inc', 'out']:
            for targetKey in ['bytes', 'packets']:
                if targetKey not in portRes[key].keys():
                    portRes[key][targetKey] = 0
                    zeroTraffic = True
        if zeroTraffic:
            self.logger.warning("Traffic statics is zero.")
        return portRes