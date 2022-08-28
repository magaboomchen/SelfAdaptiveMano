import threading
import uuid
from queue import Queue
from typing import Dict, List, Tuple

from sam.base.command import Command, CMD_TYPE_GET_SERVER_SET, CommandReply, CMD_TYPE_GET_TOPOLOGY, \
    CMD_TYPE_GET_SFCI_STATE, CMD_TYPE_ADD_SFC, CMD_TYPE_ADD_SFCI
from sam.base.messageAgent import MessageAgent, SAMMessage, MSG_TYPE_REQUEST, MSG_TYPE_SIMULATOR_CMD, SIMULATOR_ZONE
from sam.base.messageAgentAuxillary.msgAgentRPCConf import DASHBOARD_IP, DASHBOARD_PORT, MEASURER_PORT, MEASURER_IP, \
    SIMULATOR_IP, SIMULATOR_PORT
from sam.base.path import MAPPING_TYPE_MMLPSFC, ForwardingPathSet
from sam.base.rateLimiter import RateLimiterConfig
from sam.base.request import Request, Reply, REQUEST_TYPE_GET_SFCI_STATE
from sam.base.routingMorphic import RoutingMorphic, IPV4_ROUTE_PROTOCOL
from sam.base.server import Server, SERVER_TYPE_CLASSIFIER, SERVER_TYPE_NFVI
from sam.base.sfc import APP_TYPE_NORTHSOUTH_WEBSITE, SFC, SFCI
from sam.base.slo import SLO
from sam.base.test.fixtures.ipv4MorphicDict import ipv4MorphicDictTemplate
from sam.base.vnf import VNF_TYPE_RATELIMITER, VNF, PREFERRED_DEVICE_TYPE_SERVER, VNFI_RESOURCE_QUOTA_SMALL, \
    VNF_TYPE_FW, VNF_TYPE_MONITOR, VNF_TYPE_FORWARD, VNFI
from sam.test.testBase import CLASSIFIER_SERVERID, WEBSITE_REAL_IP


class Message:
    def __init__(self, dst_ip: str, dst_port: int, response_queue: Queue[SAMMessage], msg: SAMMessage):
        self.dst_ip = dst_ip
        self.dst_port = dst_port
        self.response_queue = response_queue
        self.msg = msg


class Requester:
    _message_agent: MessageAgent = None
    _request_queue: Queue[Message] = None

    @classmethod
    def _init(cls):
        Requester._request_queue = Queue()
        Requester._message_agent = MessageAgent()
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
                cls._message_agent.sendMsgByRPC(request.dst_ip, request.dst_port, request.msg)
                body = request.msg.getbody()
                if isinstance(body, Command):
                    request_id = body.cmdID
                elif isinstance(body, Request):
                    request_id = body.requestID
                else:
                    raise ValueError(f'Unknown msg body type: {type(body)}')
                response_queue_list_dict.setdefault(request_id, []).append(
                    request.response_queue)
            msg = cls._message_agent.getMsgByRPC(DASHBOARD_IP, DASHBOARD_PORT)
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

    @classmethod
    def _request(cls, request: Message) -> SAMMessage:
        if Requester._message_agent is None:
            cls._init()
        cls._request_queue.put(request)
        return request.response_queue.get(timeout=10)

    @classmethod
    def get_server_set(cls):
        # request = Message(MEASURER_IP, MEASURER_PORT, Queue(),
        #                   SAMMessage(MSG_TYPE_REQUEST, Request(0, uuid.uuid1(), REQUEST_TYPE_GET_SFCI_STATE)))
        request = Message(SIMULATOR_IP, SIMULATOR_PORT, Queue(),
                          SAMMessage(MSG_TYPE_SIMULATOR_CMD, Command(CMD_TYPE_GET_SERVER_SET, uuid.uuid1())))
        response = cls._request(request)
        return response.getbody()

    @classmethod
    def get_topo(cls):
        request = Message(SIMULATOR_IP, SIMULATOR_PORT, Queue(),
                          SAMMessage(MSG_TYPE_SIMULATOR_CMD, Command(CMD_TYPE_GET_TOPOLOGY, uuid.uuid1())))
        response = cls._request(request)
        return response.getbody()

    @classmethod
    def get_sfcis(cls):
        request = Message(SIMULATOR_IP, SIMULATOR_PORT, Queue(),
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
        request = Message(SIMULATOR_IP, SIMULATOR_PORT, Queue(),
                          SAMMessage(MSG_TYPE_SIMULATOR_CMD, cmd))
        response = cls._request(request)
        return response.getbody()
