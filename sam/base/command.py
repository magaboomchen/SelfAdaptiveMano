#!/usr/bin/python
# -*- coding: UTF-8 -*-

CMD_STATE_WAITING = "CMD_STATE_WAITING"
CMD_STATE_PROCESSING = "CMD_STATE_PROCESSING"
CMD_STATE_SUCCESSFUL = "CMD_STATE_SUCCESSFUL"
CMD_STATE_FAIL = "CMD_STATE_FAIL"

CMD_TYPE_ADD_SFC = "CMD_TYPE_ADD_SFC"
CMD_TYPE_ADD_SFCI = "CMD_TYPE_ADD_SFCI"
CMD_TYPE_DEL_SFCI = "CMD_TYPE_DEL_SFCI"
CMD_TYPE_DEL_SFC = "CMD_TYPE_DEL_SFC"
CMD_TYPE_PAUSE_BESS = "CMD_TYPE_PAUSE_BESS"
CMD_TYPE_RESUME_BESS = "CMD_TYPE_RESUME_BESS"
CMD_TYPE_GET_SERVER_SET = "CMD_TYPE_GET_SERVER_SET"
CMD_TYPE_GET_TOPOLOGY = "CMD_TYPE_GET_TOPOLOGY"
CMD_TYPE_GET_SFCI_STATE = "CMD_TYPE_GET_SFCI_STATE"
CMD_TYPE_GET_VNFI_STATE = "CMD_TYPE_GET_VNFI_STATE"
CMD_TYPE_HANDLE_SERVER_STATUS_CHANGE = "CMD_TYPE_HANDLE_SERVER_STATUS_CHANGE"
CMD_TYPE_HANDLE_FAILURE_ABNORMAL = "CMD_TYPE_HANDLE_FAILURE_ABNORMAL"
CMD_TYPE_FAILURE_ABNORMAL_RESUME = "CMD_TYPE_FAILURE_ABNORMAL_RESUME"
CMD_TYPE_GET_FLOW_SET = "CMD_TYPE_GET_FLOW_SET"
CMD_TYPE_TURN_ORCHESTRATION_ON = "CMD_TYPE_TURN_ORCHESTRATION_ON"
CMD_TYPE_TURN_ORCHESTRATION_OFF = "CMD_TYPE_TURN_ORCHESTRATION_OFF"
CMD_TYPE_GET_ORCHESTRATION_STATE = "CMD_TYPE_GET_ORCHESTRATION_STATE"
CMD_TYPE_PUT_ORCHESTRATION_STATE = "CMD_TYPE_PUT_ORCHESTRATION_STATE"
CMD_TYPE_KILL_ORCHESTRATION = "CMD_TYPE_KILL_ORCHESTRATION"
# tester use case
CMD_TYPE_TESTER_REMAP_SFCI = "CMD_TYPE_TESTER_REMAP_SFCI"


class Command(object):
    def __init__(self, cmdType, cmdID, attributes={}):
        self.cmdType = cmdType
        self.cmdID = cmdID
        self.attributes = attributes    # {'sfcUUID':sfcUUID,'sfci':sfci, 'sfc':sfc, 'classifier':classifier}

    def __str__(self):
        string = "{0}\n".format(self.__class__)
        for key,values in self.__dict__.items():
            string = string + "{0}:{1}\n".format(key, values)
        return string

    def __repr__(self):
        return str(self)


class CommandReply(object):
    def __init__(self, cmdID, cmdState, attributes={}):
        self.cmdID = cmdID
        self.cmdState = cmdState
        self.attributes = attributes    # {'switches':{},'links':{},'servers':{},'vnfis':{}}

    def __str__(self):
        string = "{0}\n".format(self.__class__)
        for key,values in self.__dict__.items():
            string = string + "{0}:{1}\n".format(key, values)
        return string

    def __repr__(self):
        return str(self)
