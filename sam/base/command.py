CMD_STATE_PROCESSING = "CMD_STATE_PROCESSING"
CMD_STATE_SUCCESSFUL = "CMD_STATE_SUCCESSFUL"
CMD_STATE_FAIL = "CMD_STATE_FAIL"

CMD_TYPE_ADD_ROUTE2INGRESS = "CMD_TYPE_ADD_ROUTE2INGRESS"
CMD_TYPE_DEL_ROUTE2INGRESS = "CMD_TYPE_DEL_ROUTE2INGRESS"
CMD_TYPE_INIT_CLASSIFIER = "CMD_TYPE_INIT_CLASSIFIER"
CMD_TYPE_ADD_SFCI = "CMD_TYPE_ADD_SFCI"
CMD_TYPE_DEL_SFCI = "CMD_TYPE_DEL_SFCI"
CMD_TYPE_ADD_CLASSIFIER_SFC = "CMD_TYPE_ADD_CLASSIFIER_SFC"
CMD_TYPE_DEL_CLASSIFIER_SFC = "CMD_TYPE_DEL_CLASSIFIER_SFC"
CMD_TYPE_GET_TOPOLOGY = "CMD_TYPE_GET_TOPOLOGY"

class Command(object):
    def __init__(self, cmdType, cmdID, sfcUUID, attributes={}):
        self.cmdType = cmdType
        self.cmdID = cmdID
        self.sfcUUID = sfcUUID
        self.attributes = attributes    # {'sfci':sfci, 'sfc':sfc, 'classifier':classifier}

class CommandReply(object):
    def __init__(self, cmdID, cmdState):
        self.cmdID = cmdID
        self.cmdState = cmdState