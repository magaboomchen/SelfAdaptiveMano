import sam

from p4nf import P4NFInstance
from agent.turbonetAgent import TurbonetAgent

from sam.base.command import CMD_TYPE_GET_SFCI_STATE, CommandReply, CMD_TYPE_ADD_SFCI, CMD_TYPE_DEL_SFCI, CMD_STATE_SUCCESSFUL, CMD_STATE_FAIL, CMD_STATE_PROCESSING
from sam.base.server import Server
from sam.base.messageAgent import SAMMessage, MessageAgent, P4CONTROLLER_QUEUE, MSG_TYPE_P4CONTROLLER_CMD, MSG_TYPE_P4CONTROLLER_CMD_REPLY, MEDIATOR_QUEUE
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.base.vnf import VNFIStatus

class P4Controller:
    def __init__(self, _zonename):
        # message init
        logConf = LoggerConfigurator(__name__, './log', 'p4Controller.log', level='debug')
        self.logger = logConf.getLogger()
        self.logger.info('Initialize P4 controller.')
        self.zoneName = _zonename
        self._messageAgent = MessageAgent()
        self.queueName = self._messageAgent.genQueueName(P4CONTROLLER_QUEUE, _zonename)
        self._messageAgent.startRecvMsg(self.queueName)
        # controller init
        self._commandsInfo = {}
        self._p4addr = '192.168.100.4:50052'
        self._p4nfi = P4NFInstance(_p4addr)

    def run(self):
        while True:
            msg = self._messageAgent.getMsg(self.queueName)
            msgType = msg.getMessageType()
            if msgType == None:
                pass
            elif msgType == MSG_TYPE_P4CONTROLLER_CMD:
                self.logger.info('Got a command.')
                cmd = msg.getbody()
                self._commandsInfo[cmd.cmdID] = {'cmd':cmd, 'state':CMD_STATE_PROCESSING}
                resDict = {}
                if cmd.cmdType == CMD_TYPE_ADD_SFCI:
                    success = self._sfciAddHandler(cmd)
                    if success:
                        self._commandsInfo[cmd.cmdID]['state'] = CMD_STATE_SUCCESSFUL
                    else:
                        self._commandsInfo[cmd.cmdID]['state'] = CMD_STATE_FAIL
                elif cmd.cmdType == CMD_TYPE_DEL_SFCI:
                    success = self._sfciDeleteHandler(cmd)
                    if success:
                        self._commandsInfo[cmd.cmdID]['state'] = CMD_STATE_SUCCESSFUL
                    else:
                        self._commandsInfo[cmd.cmdID]['state'] = CMD_STATE_FAIL
                elif cmd.cmdType == CMD_TYPE_GET_SFCI_STATE:
                    success, resDict = self._sfciStateMonitorHandler(cmd)
                    if success:
                        self._commandsInfo[cmd.cmdID]['state'] = CMD_STATE_SUCCESSFUL
                    else:
                        self._commandsInfo[cmd.cmdID]['state'] = CMD_STATE_FAIL
                else:
                    self.logger.error("Unsupported cmd type for P4 controller: %s." % cmd.cmdType)
                    self._commandsInfo[cmd.cmdID]['state'] = CMD_STATE_FAIL
                cmdRply = CommandReply(cmd.cmdID, self._commandsInfo[cmd.cmdID]['state'])
                cmdRply.attributes["zone"] = self.zoneName
                cmdRply.attributes.update(resDict)
                rplyMsg = SAMMessage(MSG_TYPE_P4CONTROLLER_CMD_REPLY, cmdRply)
                self._messageAgent.sendMsg(MEDIATOR_QUEUE, rplyMsg)
            else:
                self.logger.error('Unsupported msg type for P4 controller: %s.' % msg.getMessageType())

if __name__ == '__main__':
    zonename = 'p4controller'
    p4ctl = P4Controller(zonename)
    p4ctl.run()
