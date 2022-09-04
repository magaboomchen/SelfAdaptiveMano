import threading
import uuid
from queue import Queue
from typing import Dict, List, Tuple, Union

from sam.base.command import Command, CMD_TYPE_GET_SERVER_SET, CommandReply, CMD_TYPE_GET_TOPOLOGY, \
    CMD_TYPE_GET_SFCI_STATE, CMD_TYPE_ADD_SFC, CMD_TYPE_ADD_SFCI
from sam.base.messageAgent import MessageAgent, SAMMessage, MSG_TYPE_REQUEST, MSG_TYPE_SIMULATOR_CMD, SIMULATOR_ZONE, \
    MSG_TYPE_ABNORMAL_DETECTOR_CMD, MSG_TYPE_REGULATOR_CMD, DASHBOARD_QUEUE, REGULATOR_QUEUE
from sam.base.messageAgentAuxillary.msgAgentRPCConf import DASHBOARD_IP, DASHBOARD_PORT, MEASURER_PORT, MEASURER_IP, \
    SIMULATOR_IP, SIMULATOR_PORT, ABNORMAL_DETECTOR_IP, ABNORMAL_DETECTOR_PORT, REGULATOR_IP, REGULATOR_PORT
from sam.base.path import MAPPING_TYPE_MMLPSFC, ForwardingPathSet
from sam.base.rateLimiter import RateLimiterConfig
from sam.base.request import Request, Reply, REQUEST_TYPE_GET_SFCI_STATE, REQUEST_TYPE_ADD_SFC, REQUEST_TYPE_DEL_SFC
from sam.base.routingMorphic import RoutingMorphic, IPV4_ROUTE_PROTOCOL
from sam.base.server import Server, SERVER_TYPE_CLASSIFIER, SERVER_TYPE_NFVI
from sam.base.sfc import APP_TYPE_NORTHSOUTH_WEBSITE, SFC, SFCI
from sam.base.sfcConstant import SFC_DIRECTION_0
from sam.base.slo import SLO
from sam.base.test.fixtures.ipv4MorphicDict import ipv4MorphicDictTemplate
from sam.base.vnf import VNF_TYPE_RATELIMITER, VNF, PREFERRED_DEVICE_TYPE_SERVER, VNFI_RESOURCE_QUOTA_SMALL, \
    VNF_TYPE_FW, VNF_TYPE_MONITOR, VNF_TYPE_FORWARD, VNFI, VNF_TYPE_LB
from sam.orchestration.orchInfoBaseMaintainer import OrchInfoBaseMaintainer
from sam.test.testBase import CLASSIFIER_SERVERID, WEBSITE_REAL_IP


class MQMessage:
    def __init__(self, queue_name: str, response_queue: Queue[SAMMessage], msg: SAMMessage):
        self.queue_name = queue_name
        self.response_queue = response_queue
        self.msg = msg


class RPCMessage:
    def __init__(self, dst_ip: str, dst_port: int, response_queue: Queue[SAMMessage], msg: SAMMessage):
        self.dst_ip = dst_ip
        self.dst_port = dst_port
        self.response_queue = response_queue
        self.msg = msg


class Requester:
    _message_agent: MessageAgent = None
    _request_queue: Queue[Union[MQMessage, RPCMessage]] = None

    @classmethod
    def _init(cls):
        Requester._request_queue = Queue()
        Requester._message_agent = MessageAgent()
        Requester._message_agent.startRecvMsg(DASHBOARD_QUEUE)
        Requester._message_agent.startMsgReceiverRPCServer(DASHBOARD_IP, DASHBOARD_PORT)
        thread = threading.Thread(target=cls._message_loop)
        thread.setDaemon(True)
        thread.start()

    @classmethod
    def _message_loop(cls):
        response_queue_list_dict: Dict[uuid.UUID, List[Queue[SAMMessage]]] = {}
        while True:
            if not cls._request_queue.empty():
                request = cls._request_queue.get()
                if isinstance(request, MQMessage):
                    cls._message_agent.sendMsg(request.queue_name, request.msg)
                elif isinstance(request, RPCMessage):
                    cls._message_agent.sendMsgByRPC(request.dst_ip, request.dst_port, request.msg)
                else:
                    raise ValueError(f'Unknown msg type: {type(request)}')
                body = request.msg.getbody()
                if isinstance(body, Command):
                    request_id = body.cmdID
                elif isinstance(body, Request):
                    request_id = body.requestID
                else:
                    raise ValueError(f'Unknown msg body type: {type(body)}')
                if request.response_queue is not None:
                    response_queue_list_dict.setdefault(request_id, []).append(
                        request.response_queue)

            def _handle_message(msg: SAMMessage):
                msg_type = msg.getMessageType()
                if msg_type is not None:
                    body = msg.getbody()
                    if isinstance(body, CommandReply):
                        response_id = body.cmdID
                    elif isinstance(body, Reply):
                        response_id = body.requestID
                    else:
                        raise ValueError(f'Unknown msg body type: {type(body)}')
                    response_queue = response_queue_list_dict[response_id].pop(0)
                    response_queue.put(msg)

            msg = cls._message_agent.getMsgByRPC(DASHBOARD_IP, DASHBOARD_PORT)
            _handle_message(msg)
            msg = cls._message_agent.getMsg(DASHBOARD_QUEUE)
            _handle_message(msg)

    @classmethod
    def _request(cls, request: Union[MQMessage, RPCMessage]) -> SAMMessage:
        if Requester._message_agent is None:
            cls._init()
        cls._request_queue.put(request)
        if request.response_queue is not None:
            return request.response_queue.get(timeout=10)
        return None

    @classmethod
    def get_server_set(cls):
        # request = Message(MEASURER_IP, MEASURER_PORT, Queue(),
        #                   SAMMessage(MSG_TYPE_REQUEST, Request(0, uuid.uuid1(), REQUEST_TYPE_GET_SFCI_STATE)))
        request = RPCMessage(SIMULATOR_IP, SIMULATOR_PORT, Queue(),
                             SAMMessage(MSG_TYPE_SIMULATOR_CMD, Command(CMD_TYPE_GET_SERVER_SET, uuid.uuid1())))
        response = cls._request(request)
        return response.getbody()

    @classmethod
    def get_topo(cls):
        request = RPCMessage(SIMULATOR_IP, SIMULATOR_PORT, Queue(),
                             SAMMessage(MSG_TYPE_SIMULATOR_CMD, Command(CMD_TYPE_GET_TOPOLOGY, uuid.uuid1())))
        response = cls._request(request)
        return response.getbody()

    @classmethod
    def get_sfcis(cls):
        request = RPCMessage(SIMULATOR_IP, SIMULATOR_PORT, Queue(),
                             SAMMessage(MSG_TYPE_SIMULATOR_CMD, Command(CMD_TYPE_GET_SFCI_STATE, uuid.uuid1())))
        response = cls._request(request)
        return response.getbody()

    @classmethod
    def add_sfci(cls):
        CLASSIFIER_DATAPATH_IP = "2.2.0.2"
        classifier = Server("ens3", CLASSIFIER_DATAPATH_IP, SERVER_TYPE_CLASSIFIER)
        classifier.setServerID(CLASSIFIER_SERVERID)
        classifier._serverDatapathNICIP = CLASSIFIER_DATAPATH_IP
        classifier._ifSet["ens3"] = {}
        classifier._ifSet["ens3"]["IP"] = "192.168.0.194"
        classifier._serverDatapathNICMAC = "00:1b:21:c0:8f:ae"
        sfcLength = 1
        sfcUUID = uuid.uuid1()
        vNFTypeSequence = [VNF_TYPE_RATELIMITER] * sfcLength
        vnfSequence = [VNF(uuid.uuid1(), VNF_TYPE_RATELIMITER,
                           RateLimiterConfig(maxMbps=100),
                           PREFERRED_DEVICE_TYPE_SERVER)] * sfcLength
        maxScalingInstanceNumber = 1
        backupInstanceNumber = 0
        applicationType = APP_TYPE_NORTHSOUTH_WEBSITE
        routingMorphic = RoutingMorphic()
        routingMorphic.from_dict(ipv4MorphicDictTemplate)
        direction1 = {
            'ID': 0,
            'source': {'node': None, 'IPv4': "*"},
            'ingress': classifier,
            'match': {'srcIP': "*", 'dstIP': WEBSITE_REAL_IP,
                      'srcPort': "*", 'dstPort': "*", 'proto': "*"},
            'egress': classifier,
            'destination': {'node': None, 'IPv4': WEBSITE_REAL_IP}
        }
        directions = [direction1]
        slo = SLO(latency=35, throughput=0.1)
        sfc = SFC(sfcUUID, vNFTypeSequence, maxScalingInstanceNumber,
                  backupInstanceNumber, applicationType, directions,
                  {'zone': SIMULATOR_ZONE}, slo=slo,
                  routingMorphic=routingMorphic,
                  vnfSequence=vnfSequence,
                  vnfiResourceQuota=VNFI_RESOURCE_QUOTA_SMALL)
        SFF1_DATAPATH_IP = "2.2.96.3"
        SFF1_DATAPATH_MAC = "b8:ca:3a:65:f7:fa"  # ignore this
        SFF1_CONTROLNIC_IP = "192.168.8.17"  # ignore this
        SFF1_CONTROLNIC_MAC = "b8:ca:3a:65:f7:f8"  # ignore this
        SFF1_SERVERID = 11281
        vnfiSequence = []
        vnfType = VNF_TYPE_RATELIMITER
        for index in range(sfcLength):
            vnfiSequence.append([])
            for iN in range(1):
                server = Server("ens3", SFF1_DATAPATH_IP, SERVER_TYPE_NFVI)
                server.setServerID(SFF1_SERVERID)
                server.setControlNICIP(SFF1_CONTROLNIC_IP)
                server.setControlNICMAC(SFF1_CONTROLNIC_MAC)
                server.setDataPathNICMAC(SFF1_DATAPATH_MAC)
                if vnfType == VNF_TYPE_RATELIMITER:
                    config = RateLimiterConfig(maxMbps=100)
                elif vnfType == VNF_TYPE_MONITOR:
                    config = None
                else:
                    config = None
                vnfi = VNFI(vnfType, vnfType=vnfType,
                            vnfiID=uuid.uuid1(), config=config, node=server)
                vnfiSequence[index].append(vnfi)
        d0FP = [
            [(0, CLASSIFIER_SERVERID), (0, 0), (0, 256), (0, 768), (0, SFF1_SERVERID)],  # (stageIndex, nodeID)
            [(1, SFF1_SERVERID), (1, 768), (1, 256), (1, 0), (1, CLASSIFIER_SERVERID)]
        ]
        primaryForwardingPath = {1: d0FP}
        mappingType = MAPPING_TYPE_MMLPSFC  # This is your mapping algorithm type
        backupForwardingPath = {}  # you don't need to care about backupForwardingPath
        forwardingPathSet = ForwardingPathSet(primaryForwardingPath, mappingType,
                                              backupForwardingPath)
        sfci = SFCI(1, vnfiSequence, None, forwardingPathSet)
        cmdID = uuid.uuid1()
        attr = {'sfc': sfc, 'sfci': sfci}
        cmd = Command(CMD_TYPE_ADD_SFCI, cmdID, attr)
        request = RPCMessage(SIMULATOR_IP, SIMULATOR_PORT, Queue(),
                             SAMMessage(MSG_TYPE_SIMULATOR_CMD, cmd))
        response = cls._request(request)
        return response.getbody()

    @classmethod
    def add_sfc(cls, req: dict):
        direction = {
            'ID': SFC_DIRECTION_0,
            'source': {
                'node': None,
                'IPv4': "*"
            },
            'destination': {
                'node': None,
                'IPv4': "*"
            },
            'match': {}
        }
        vnfSequence = []
        for vnfType in req['vnfType']:
            config = None
            if vnfType == VNF_TYPE_RATELIMITER:
                config = RateLimiterConfig(100)
            if req['vnfMorphic'] == 'AUTO':
                vnfSequence.append(VNF(uuid.uuid1(), vnfType, config))
            else:
                vnfSequence.append(VNF(uuid.uuid1(), vnfType, config, preferredDeviceType=req['vnfMorphic']))
        sfc = SFC(uuid.uuid1(), req['vnfType'], 10, 0,
                  req['applicationType'], [direction],
                  attributes={'zone': req['zone']}, vnfSequence=vnfSequence,
                  vnfiResourceQuota=VNFI_RESOURCE_QUOTA_SMALL, slo=SLO(throughput=1),
                  routingMorphic=req['routingMorphic'], scalingMode=req['scalingMode'])
        request = MQMessage(REGULATOR_QUEUE, None, SAMMessage(MSG_TYPE_REGULATOR_CMD,
                                                              Request(0, uuid.uuid1(), REQUEST_TYPE_ADD_SFC,
                                                                      attributes={'sfc': sfc,
                                                                                  'zone': req['zone']})))
        cls._request(request)

    @classmethod
    def get_sfc(cls):
        oib = OrchInfoBaseMaintainer("localhost", "dbAgent", "123", reInitialTable=False)
        sfcs = oib.getAllSFC()
        sfc_dicts = []
        for sfc in sfcs:
            sfc_dicts.append({
                'zone': sfc[0],
                'uuid': str(sfc[1]),
                'sfcis': sfc[2],
                'state': sfc[3],
                'sfc': sfc[4].to_dict()
            })
            sfc_dicts[-1]['sfc']['source']['node'] = sfc_dicts[-1]['sfc']['source']['node'].getNodeID()
            sfc_dicts[-1]['sfc']['destination']['node'] = sfc_dicts[-1]['sfc']['destination']['node'].getNodeID()
        return sfc_dicts

    @classmethod
    def del_sfc(cls, sfcUUID: str):
        oib = OrchInfoBaseMaintainer("localhost", "dbAgent", "123", reInitialTable=False)
        sfc = oib.getSFC4DB(uuid.UUID(sfcUUID))
        oib.delSFC(uuid.UUID(sfcUUID))
        request = MQMessage(REGULATOR_QUEUE, None, SAMMessage(MSG_TYPE_REGULATOR_CMD,
                                                              Request(0, uuid.uuid1(), REQUEST_TYPE_DEL_SFC,
                                                                      attributes={'sfc': sfc,
                                                                                  'zone': SIMULATOR_ZONE})))
        cls._request(request)
