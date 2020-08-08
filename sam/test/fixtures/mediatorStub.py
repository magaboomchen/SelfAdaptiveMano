from sam.base.messageAgent import *
from sam.base.command import *
from sam.test.fixtures.orchestrationStub import *

VNFI1_IP = "2.2.0.39"
WEBSITE_VIRTUAL_IP = "2.2.2.2"
WEBSITE_REAL_IP = "192.168.122.1"
CLASSIFIER_DATAPATH_IP = "2.2.0.35"
CLASSIFIER_DATAPATH_MAC = "52:54:00:05:4D:7D"
CLASSIFIER_CONTROL_IP = "2.2.122.34"

class MediatorStub(OrchestrationStub):
    def __init__(self):
        self.mA = MessageAgent()
        self.mA.startRecvMsg(MEDIATOR_QUEUE)

    def sendCMDInitClassifier(self, sfc):
        classifierSet = {}
        for direction in sfc.directions:
            classifier = direction['ingress']
            serverID = classifier.getServerID()
            if not serverID in classifierSet:
                classifierSet[serverID] = classifier

        for classifier in classifierSet.itervalues():
            cmdID = uuid.uuid1()
            attr = {'classifier':classifier,'sfcUUID':sfc.sfcUUID}
            body = Command(CMD_TYPE_INIT_CLASSIFIER,cmdID,attr)
            msg = SAMMessage(MSG_TYPE_CLASSIFIER_CONTROLLER_CMD, body)
            self.mA.sendMsg(SERVER_CLASSIFIER_CONTROLLER_QUEUE, msg)

    def genCMDAddSFCI(self,sfc,sfci):
        cmdID = uuid.uuid1()
        attr = {'sfc':sfc,'sfci':sfci,'sfcUUID':sfc.sfcUUID}
        cmd = Command(CMD_TYPE_ADD_SFCI,cmdID,attr)
        return cmd

    def genCMDDelSFCI(self,sfc,sfci):
        cmdID = uuid.uuid1()
        attr = {'sfc':sfc,'sfci':sfci,'sfcUUID':sfc.sfcUUID}
        cmd = Command(CMD_TYPE_DEL_SFCI,cmdID,attr)
        return cmd