import logging

from sam.base.messageAgent import *
from sam.base.sfc import *
from sam.base.command import *
from sam.base.server import *
from sam.serverController.vnfController.vnfiAdder import *

# port for docker tcp connect
# (maybe unsafe, to modify in the future)
DOCKER_TCP_PORT = 5982

# vnfi states
VNFI_STATE_PROCESSING = 'VNFI_STATE_PROCESSING'
VNFI_STATE_DEPLOYED = 'VNFI_STATE_DEPLOYED'
VNFI_STATE_FAILED = 'VNFI_STATE_FAILED'

class VNFController(object):
    def __init__(self):
        logging.info('Initialize vnf controller.')

        self._commandsInfo = {}

        self._vnfiInfo = {} # key:vnfiID, value:{'vnfi':vnfi,'state':VNFI_STATE,'error':exception}

        self._vnfiAdder = VNFIAdder(DOCKER_TCP_PORT)

        self._messageAgent = MessageAgent()
        self._messageAgent.startRecvMsg(MEDIATOR_QUEUE)

    def startVNFController(self):
        while True:
            msg = self._messageAgent.getMsg(VNF_CONTROLLER_QUEUE)
            msgType = msg.getMessageType()
            if msgType == None:
                pass
            elif msgType == MSG_TYPE_VNF_CONTROLLER_CMD:
                cmd = msg.getbody()
                self._commandsInfo[cmd.cmdID] = {'cmd':cmd, 'state':CMD_STATE_PROCESSING}
                if cmd.cmdType == CMD_TYPE_ADD_SFCI:
                    self._sfciAddHandler(cmd)
                    # TODO: modify cmd info
                elif cmd.cmdType == CMD_TYPE_DEL_SFCI:
                    self._sfciDeleteHandler(cmd)
                    # TODO: modify cmd info
                else:
                    logging.error("Unsupported cmd type for vnf controller: %s." % cmd.cmdType)
                    self._commandsInfo[cmd.cmdID] = CMD_STATE_FAIL
                rplyMsg = SAMMessage(MSG_TYPE_VNF_CONTROLLER_CMD_REPLY,
                    CommandReply(cmd.cmdID, self._commandsInfo[cmd.cmdID]['state']))
                self._messageAgent.sendMsg(MEDIATOR_QUEUE, rplyMsg)
            else:
                logging.error('Unsupported msg type for vnf controller: %s.' % msg.getMessageType())

    def _sfciAddHandler(self, cmd):
        vnfSeq = cmd.attributes['sfci'].VNFISequence
        for vnf in vnfSeq:
            for vnfi in vnf:
                if isinstance(vnfi.node, Server):
                    self._vnfiInfo[vnfi.VNFIID] = {'vnfi':vnfi, 'state':VNFI_STATE_PROCESSING, 'error': None}
                    try:
                        self._vnfiAdder.addVNFI(vnfi)
                    except Exception as exp:
                        self._vnfiInfo[vnfi.VNFIID]['state'] = VNFI_STATE_FAILED
                        self._vnfiInfo[vnfi.VNFIID]['error'] = exp
    
    
    def _sfciDeleteHandler(self, cmd):
        # TODO
        pass