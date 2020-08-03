from sam.base.messageAgent import *
from sam.base.command import *

VNFI1_IP = "192.168.0.39"
WEBSITE_VIRTUAL_IP = "2.2.2.2"
WEBSITE_REAL_IP = "192.168.122.1"
CLASSIFIER_DATAPATH_IP = "192.168.0.35"
CLASSIFIER_DATAPATH_MAC = "52:54:00:05:4D:7D"
CLASSIFIER_CONTROL_IP = "192.168.122.34"

class OrchestrationStub(object):
    def __init__(self):
        self.mA = MessageAgent()
        self.mA.startRecvMsg(ORCHESTRATION_MODULE_QUEUE)

    def sendCMDInitClassifier(self, sfc):
        classifierSet = {}
        for direction in sfc.directions:
            classifier = direction['ingress']
            serverID = classifier.getServerID()
            if not serverID in classifierSet:
                classifierSet[serverID] = classifier

        for classifier in classifierSet.itervalues():
            cmdID = uuid.uuid1()
            attr = {'classifier':classifier}
            body = Command(CMD_TYPE_INIT_CLASSIFIER,cmdID,sfc.sfcUUID,attr)
            msg = SAMMessage(MSG_TYPE_CLASSIFIERCMD, body)
            self.mA.sendMsg(CLASSIFIER_CONTROLLER_QUEUE, msg)

    def sendCMDAddSFC(self, sfc):
        cmdID = uuid.uuid1()
        attr = {'sfc':sfc}
        body = Command(CMD_TYPE_ADD_CLASSIFIER_SFC,cmdID,sfc.sfcUUID,attr)
        msg = SAMMessage(MSG_TYPE_CLASSIFIERCMD, body)
        self.mA.sendMsg(CLASSIFIER_CONTROLLER_QUEUE, msg)
        return [cmdID,sfc.sfcUUID]

    def sendCMDDelSFC(self, sfc):
        cmdID = uuid.uuid1()
        attr = {'sfc':sfc}
        body = Command(CMD_TYPE_DEL_CLASSIFIER_SFC,cmdID,sfc.sfcUUID,attr)
        msg = SAMMessage(MSG_TYPE_CLASSIFIERCMD, body)
        self.mA.sendMsg(CLASSIFIER_CONTROLLER_QUEUE, msg)
        return [cmdID,sfc.sfcUUID]

    def sendCMDAddSFCI(self,sfc,sfci):
        cmdID = uuid.uuid1()
        attr = {'sfc':sfc,'sfci':sfci}
        body = Command(CMD_TYPE_ADD_SFCI,cmdID,sfc.sfcUUID,attr)
        msg = SAMMessage(MSG_TYPE_CLASSIFIERCMD, body)
        self.mA.sendMsg(CLASSIFIER_CONTROLLER_QUEUE, msg)
        return [cmdID,sfc.sfcUUID]

    def sendCMDDelSFCI(self,sfc,sfci):
        cmdID = uuid.uuid1()
        attr = {'sfc':sfc,'sfci':sfci}
        body = Command(CMD_TYPE_DEL_SFCI,sfc.sfcUUID,attr)
        msg = SAMMessage(MSG_TYPE_CLASSIFIERCMD, body)
        self.mA.sendMsg(CLASSIFIER_CONTROLLER_QUEUE, msg)
        return [cmdID,sfc.sfcUUID]

