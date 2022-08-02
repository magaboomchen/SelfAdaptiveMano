import sam

from agent.p4Agent import P4Agent
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
        self._commands = {}
        self._sfclist = {}
        self._p4agent = {}
        self._p4agent[0] = P4Agent('192.168.100.4:50052')
        # self._p4agent[1] = P4Agent('192.168.100.5:50052')
        self.logger.info('P4 controller initialization complete.')

    def run(self):
        while True:
            msg = self._messageAgent.getMsg(self.queueName)
            msgType = msg.getMessageType()
            if msgType == None:
                pass
            elif msgType == MSG_TYPE_P4CONTROLLER_CMD:
                self.logger.info('Got a command.')
                cmd = msg.getbody()
                self._commands[cmd.cmdID] = cmd
                resDict = {}
                if cmd.cmdType == CMD_TYPE_ADD_SFC:
                    pass
                elif cmd.cmdType == CMD_TYPE_DEL_SFC:
                    pass
                elif cmd.cmdType == CMD_TYPE_ADD_SFCI:
                    pass
                elif cmd.cmdType == CMD_TYPE_DEL_SFCI:
                    pass
                elif cmd.cmdType == CMD_TYPE_GET_SFCI_STATE:
                    pass
                else:
                    self.logger.error("Unsupported cmd type for P4 controller: %s." % cmd.cmdType)
            else:
                self.logger.error('Unsupported msg type for P4 controller: %s.' % msg.getMessageType())
    
    def _addsfc(self):
        pass
    
    def _addsfci(self):
        pass
    
    def _getstate(self):
        pass
    
    def _delsfc(self):
        pass
    
    def _delsfci(self):
        pass

if __name__ == '__main__':
    zonename = 'p4controller'
    p4ctl = P4Controller(zonename)
    p4ctl.run()
