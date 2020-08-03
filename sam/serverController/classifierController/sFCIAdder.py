from sam.serverController.bessGRPC import *

class SFCIAdder(BessGRPC):
    def __init__(self,clsMaintainer):
        self.clsMaintainer = clsMaintainer
        # TODO : replace self._classifierSet

    def addSFCI(self,cmd):
        sfc = cmd.attributes['sfc']
        sfci = cmd.attributes['sfci']
        for direction in sfc.directions:
            ingress = direction['ingress']
            serverID = ingress.getServerID()
            if not serverID in self._classifierSet.iterkeys():
                raise ValueError('classifier has not been initialized yet.')
            sfcUUID = sfc.sfcUUID
            if self._classifierSet[serverID]["sfcSet"].has_key(sfcUUID):
                raise ValueError('classifier has added SFC already.')
            if self._classifierSet[serverID]["sfcSet"][sfcUUID].has_key(sfci.SFCIID):
                raise ValueError('classifier has added SFCI already.')
            self._classifierSet[serverID]["sfcSet"][sfcUUID][sfci.SFCIID] = {"sfci":sfci,"hashLBGate":None}
            self._addSFCIaddModules(sfc,sfci,direction)
            self._addSFCIaddRules(sfc,sfci,direction)
            self._addSFCIaddLinks(sfc,sfci,direction)

    def _addSFCIaddModules(self,sfc,sfci,direction):
        ingress = direction['ingress']
        sfcUUID = sfc.sfcUUID
        bessServerUrl = ingress.getControlNICIP() + ":10514"
        SFCIID = sfci.SFCIID
        logging.info(bessServerUrl)
        with grpc.insecure_channel(bessServerUrl) as channel:
            stub = service_pb2_grpc.BESSControlStub(channel)
            stub.PauseAll(bess_msg_pb2.EmptyRequest())

            moduleNamePostfix = str(SFCIID) + '_' + str(direction['ID'])

            # GenericDecap()
            argument = Any()
            arg = module_msg_pb2.GenericDecapArg(bytes=14)
            argument.Pack(arg)
            response = stub.CreateModule(bess_msg_pb2.CreateModuleRequest(
                name="GenericDecap_"+moduleNamePostfix,mclass="GenericDecap",
                arg=argument))
            self._checkResponse(response)

            # SetMetaData()
            argument = Any()
            tunnelSrcIP = self._sc.aton(ingress.getDatapathNICIP())
            if direction['ID'] == 0:
                VNFID = sfci.vNFTypeSequence[0]
                PathID = DIRECTION1_PATHID_OFFSET
            else:
                VNFID = sfci.vNFTypeSequence[-1]
                PathID = DIRECTION2_PATHID_OFFSET
            tunnelDstIP = self._sc.aton(self._genIP4SVPIDs(SFCIID,VNFID,PathID))
            arg = module_msg_pb2.SetMetadataArg(attrs=[
                {'name':"ip_src", 'size':4, 'value_bin':tunnelSrcIP},
                {'name':"ip_dst", 'size':4, 'value_bin':tunnelDstIP},
                {'name':"ip_proto", 'size':2, 'value_bin':b'\x08\x00'},
            ])
            argument.Pack(arg)
            response = stub.CreateModule(bess_msg_pb2.CreateModuleRequest(
                name="smd_"+moduleNamePostfix,mclass="SetMetadata",arg=argument))
            self._checkResponse(response)

            # IPEncap()
            argument = Any()
            arg = module_msg_pb2.IPEncapArg()
            argument.Pack(arg)
            response = stub.CreateModule(bess_msg_pb2.CreateModuleRequest(
                name="ipe_"+moduleNamePostfix,mclass="IPEncap",arg=argument))
            self._checkResponse(response)

            stub.ResumeAll(bess_msg_pb2.EmptyRequest())

    def _genIP4SVPIDs(self,sfcID,vnfID,pathID):
        return ((sfcID & 0xFFF) << 12) + ((vnfID & 0xF) << 8) + (pathID & 0xFF)

    def _addSFCIaddRules(self,sfc,sfci,direction):
        bessServerUrl = ingress.getControlNICIP() + ":10514"
        with grpc.insecure_channel(bessServerUrl) as channel:
            stub = service_pb2_grpc.BESSControlStub(channel)
            stub.PauseAll(bess_msg_pb2.EmptyRequest())

            SFCUUID = sfc.SFCUUID
            moduleNamePostfix = str(SFCUUID)
            hashLBName = "hlb_"+moduleNamePostfix

            # add hash LB gate
            argument = Any()
            gate = self._genhlbGateNum(hashLBName,serverID,sfcUUID)
            self._gethlbRule()
            arg = module_msg_pb2.HashLBCommandSetGatesArg(gates=[

            ])
            argument.Pack(arg)
            response = stub.ModuleCommand(bess_msg_pb2.CommandRequest(
                name="wm2",cmd="add",arg=argument))

            stub.ResumeAll(bess_msg_pb2.EmptyRequest())

        # TODO: hash lb add gate

    def _genhlbGateNum(hashLBName,serverID,sfcUUID):
        self._classifierSet[serverID]["sfcSet"][sfcUUID][sfci.SFCIID]

    def _addSFCIaddLinks(self,sfc,sfci,direction):
        ingress = direction['ingress']
        sfcUUID = sfc.sfcUUID
        bessServerUrl = ingress.getControlNICIP() + ":10514"
        SFCIID = sfci.SFCIID
        logging.info(bessServerUrl)
        with grpc.insecure_channel(bessServerUrl) as channel:
            stub = service_pb2_grpc.BESSControlStub(channel)
            stub.PauseAll(bess_msg_pb2.EmptyRequest())

            moduleNamePostfix = str(SFCIID) + '_' + str(direction['ID'])
            lbNamePostfix = str(sfcUUID)

            # Connection
            # hlb: gate -> gd
            ogate = 0 # TODO : get hlb ogate
            response = stub.ConnectModules(bess_msg_pb2.ConnectModulesRequest(
                m1="hlb_"+lbNamePostfix,m2=ogate,ogate=ogate,igate=0))
            self._checkResponse(response)

            # gd -> sma



            # sma -> ipe



            # ipe -> ee


            stub.ResumeAll(bess_msg_pb2.EmptyRequest())

