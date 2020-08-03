from sam.serverController.bessGRPC import *

class SFCAdder(BessGRPC):
    def __init__(self,clsMaintainer):
        self.clsMaintainer = clsMaintainer
        # TODO : replace self._classifierSet

    def addSFC(self,cmd):
        sfc = cmd.attributes['sfc']
        for direction in sfc.directions:
            ingress = direction['ingress']
            serverID = ingress.getServerID()
            if not serverID in self._classifierSet.iterkeys():
                raise ValueError('classifier has not initialized yet.')
            sfcUUID = sfc.sfcUUID
            if self._classifierSet[serverID]["sfcSet"].has_key(sfcUUID):
                raise ValueError('classifier has add SFC already.')
            self._classifierSet[serverID]["sfcSet"][sfcUUID] = {}   # {"wm2ogate":x,SFCIID:{"sfci":sfci,"hashLBGate":y}}
            self._addSFCaddModules(ingress,sfcUUID)
            self._addSFCaddRules(ingress,sfcUUID,direction)
            self._addSFCaddLinks(ingress,sfcUUID)

    def _addSFCaddModules(self,ingress,sfcUUID):
        bessServerUrl = ingress.getControlNICIP() + ":10514"
        logging.info(bessServerUrl)
        with grpc.insecure_channel(bessServerUrl) as channel:
            stub = service_pb2_grpc.BESSControlStub(channel)
            stub.PauseAll(bess_msg_pb2.EmptyRequest())

            moduleNamePostfix = str(sfcUUID)

            # HashLB()
            argument = Any()
            arg = module_msg_pb2.HashLBArg(mode="l3")
            argument.Pack(arg)
            response = stub.CreateModule(bess_msg_pb2.CreateModuleRequest(
                name="hlb_"+moduleNamePostfix,mclass="HashLB",arg=argument))
            self._checkResponse(response)

            stub.ResumeAll(bess_msg_pb2.EmptyRequest())

    def _addSFCaddRules(self,ingress,sfcUUID,direction):
        bessServerUrl = ingress.getControlNICIP() + ":10514"
        logging.info(bessServerUrl)
        match = direction['match']
        serverID = ingress.getServerID()
        with grpc.insecure_channel(bessServerUrl) as channel:
            stub = service_pb2_grpc.BESSControlStub(channel)
            stub.PauseAll(bess_msg_pb2.EmptyRequest())

            # Rule
            # Add match
            argument = Any()
            gate = self._genwm2GateNum(serverID,sfcUUID)
            [values,masks] = self._getwm2Rule(match)
            arg = module_msg_pb2.WildcardMatchCommandAddArg(gate=gate,
                values=values, masks=masks)
            argument.Pack(arg)
            response = stub.ModuleCommand(bess_msg_pb2.CommandRequest(
                name="wm2",cmd="add",arg=argument))

            stub.ResumeAll(bess_msg_pb2.EmptyRequest())

    def _genwm2GateNum(self,serverID,sfcUUID):
        num = len(self._classifierSet[serverID]["sfcSet"]) + 1
        self._classifierSet[serverID]["sfcSet"][sfcUUID]["wm2ogate"] = num
        return num

    def _getwm2GateNum(self,serverID,sfcUUID):
        return self._classifierSet[serverID]["sfcSet"][sfcUUID]["wm2ogate"]

    def _getwm2Rule(self,match):
        values=[
            {"value_bin":b'\x00'},
            {"value_bin":b'\x00\x00\x00\x00\x00\x00\x00\x00'},
            {"value_bin":b'\x00\x00\x00\x00\x00\x00\x00\x00'},
            {"value_bin":b'\x00\x00'},
            {"value_bin":b'\x00\x00'}
        ]
        masks=[
            {'value_bin':b'\x00'},
            {'value_bin':b'\x00\x00\x00\x00\x00\x00\x00\x00'},
            {'value_bin':b'\x00\x00\x00\x00\x00\x00\x00\x00'},
            {'value_bin':b'\x00\x00'},
            {'value_bin':b'\x00\x00'}
        ]
        if match['proto'] != None:
            values[0]["value_bin"] = match['proto']
            masks[0]["value_bin"] = b'\xFF'
        if match['srcIP'] != None:
            values[1]["value_bin"] = self._sc.aton(match['srcIP'])
            masks[1]["value_bin"] = b'\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF'
        if match['dstIP'] != None:
            values[2]["value_bin"] = self._sc.aton(match['dstIP'])
            masks[2]["value_bin"] = b'\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF'
        if match['srcPort'] != None:
            values[3]["value_bin"] = self._sc.aton(match['srcPort'])
            masks[3]["value_bin"] = b'\xFF\xFF\xFF\xFF'
        if match['dstPort'] != None:
            values[4]["value_bin"] = self._sc.aton(match['dstPort'])
            masks[4]["value_bin"] = b'\xFF\xFF\xFF\xFF'
        return [values,masks]

    def _addSFCaddLinks(self,ingress,sfcUUID):
        bessServerUrl = ingress.getControlNICIP() + ":10514"
        logging.info(bessServerUrl)
        serverID = ingress.getServerID()
        with grpc.insecure_channel(bessServerUrl) as channel:
            stub = service_pb2_grpc.BESSControlStub(channel)
            stub.PauseAll(bess_msg_pb2.EmptyRequest())

            moduleNamePostfix = str(sfcUUID)

            # Connection
            # wm2 -> HashLB()'s name
            ogate = self._getwm2GateNum(serverID,sfcUUID)
            response = stub.ConnectModules(bess_msg_pb2.ConnectModulesRequest(
                m1="wm2",m2="hlb_"+moduleNamePostfix,ogate=ogate,igate=0))
            self._checkResponse(response)

            stub.ResumeAll(bess_msg_pb2.EmptyRequest())

