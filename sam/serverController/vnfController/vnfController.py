import logging

from sam.base.messageAgent import *
from sam.base.sfc import *
from sam.base.vnf import *
from sam.base.command import *
from sam.base.server import *
from sam.serverController.vnfController.vnfiAdder import *
from sam.serverController.vnfController.vnfMaintainer import *

# port for docker tcp connect
# (maybe unsafe, to modify in the future)
DOCKER_TCP_PORT = 5982

class VNFController(object):
    def __init__(self):
        logging.info('Initialize vnf controller.')

        self._commandsInfo = {}

        self._vnfiAdder = VNFIAdder(DOCKER_TCP_PORT)
        self._vnfiMaintainer = VNFIMaintainer()

        self._messageAgent = MessageAgent()
        self._messageAgent.startRecvMsg(VNF_CONTROLLER_QUEUE)

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
                    success = self._sfciAddHandler
                    if success:
                        self._commandsInfo[cmd.cmdID]['state'] = CMD_STATE_SUCCESSFUL
                    else:
                        # TODO
                        pass               
                elif cmd.cmdType == CMD_TYPE_DEL_SFCI:
                    self._sfciDeleteHandler(cmd)
                    success = self._sfciDeleteHandler
                    if success:
                        self._commandsInfo[cmd.cmdID]['state'] = CMD_STATE_SUCCESSFUL
                    else:
                        # TODO
                        pass
                else:
                    logging.error("Unsupported cmd type for vnf controller: %s." % cmd.cmdType)
                    self._commandsInfo[cmd.cmdID]['state'] = CMD_STATE_FAIL
                rplyMsg = SAMMessage(MSG_TYPE_VNF_CONTROLLER_CMD_REPLY,
                    CommandReply(cmd.cmdID, self._commandsInfo[cmd.cmdID]['state']))
                self._messageAgent.sendMsg(MEDIATOR_QUEUE, rplyMsg)
            else:
                logging.error('Unsupported msg type for vnf controller: %s.' % msg.getMessageType())

    def _sfciAddHandler(self, cmd):
        sfciID = cmd.attributes['sfci'].SFCIID
        # TODO: if sfciID in vnfMaintainer?
        self._vnfiMaintainer.addSFCI(sfciID)
        vnfSeq = cmd.attributes['sfci'].VNFISequence
        success = True
        for vnf in vnfSeq:
            for vnfi in vnf:
                if isinstance(vnfi.node, Server):
                    # TODO: if vnfi in vnfMaintaine?
                    self._vnfiMaintainer.addVNFI(sfciID, vnfi)
                    try:
                        container = self._vnfiAdder.addVNFI(vnfi)
                        self._vnfiMaintainer.setVNFIState(sfciID, vnfi, VNFI_STATE_DEPLOYED)
                        self._vnfiMaintainer.setVNFIContainer(sfciID, vnfi, container)
                    except Exception as exp:
                        self._vnfiMaintainer.setVNFIState(sfciID, vnfi, VNFI_STATE_FAILED)
                        self._vnfiMaintainer.setVNFIError(sfciID, vnfi, exp)    
                        success = False
        return success
                        

    def _sfciDeleteHandler(self, cmd):
        # TODO
        pass

if __name__=="__main__":
    logging.basicConfig(level=logging.INFO)
    vc = VNFController()
    vc.startVNFController()