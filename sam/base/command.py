#!/usr/bin/python
# -*- coding: UTF-8 -*-

from uuid import UUID
from typing import Any, Dict, Union

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
CMD_TYPE_ORCHESTRATION_UPDATE_EQUIPMENT_STATE = "CMD_TYPE_ORCHESTRATION_UPDATE_EQUIPMENT_STATE"
CMD_TYPE_ORCHESTRATION_MANAGER_UPDATE_STATE = "CMD_TYPE_ORCHESTRATION_MANAGER_UPDATE_STATE"
CMD_TYPE_KILL_ORCHESTRATION = "CMD_TYPE_KILL_ORCHESTRATION"
# tester use case
CMD_TYPE_TESTER_REMAP_SFCI = "CMD_TYPE_TESTER_REMAP_SFCI"
# turbonet 
CMD_TYPE_ADD_NSH_ROUTE = "CMD_TYPE_ADD_NSH_ROUTE"
CMD_TYPE_DEL_NSH_ROUTE = "CMD_TYPE_DEL_NSH_ROUTE"
CMD_TYPE_ADD_CLASSIFIER_ENTRY = "CMD_TYPE_ADD_CLASSIFIER"
CMD_TYPE_DEL_CLASSIFIER_ENTRY = "CMD_TYPE_DEL_CLASSIFIER"
# abnormal detector
CMD_TYPE_ABNORMAL_DETECTOR_QUERY = "CMD_TYPE_ABNORMAL_DETECTOR_QUERY"


class Command(object):
    def __init__(self, cmdType, cmdID, attributes=None):
        # type: (Union[CMD_TYPE_ADD_SFC, CMD_TYPE_ADD_SFCI, CMD_TYPE_DEL_SFCI, CMD_TYPE_DEL_SFC], UUID, Dict[str, Any]) -> None
        self.cmdType = cmdType
        self.cmdID = cmdID
        if attributes == None:
            self.attributes = {}    # {'sfcUUID':sfcUUID,'sfci':SFCI, 'sfc':SFC, 'classifier':classifier}
        else:
            self.attributes = attributes

    def __str__(self):
        string = "{0}\n".format(self.__class__)
        for key,values in self.__dict__.items():
            string = string + "{0}:{1}\n".format(key, values)
        return string

    def __repr__(self):
        return str(self)


class CommandReply(object):
    def __init__(self, cmdID, cmdState, attributes=None):
        # type: (UUID, Union[CMD_STATE_WAITING, CMD_STATE_PROCESSING, CMD_STATE_SUCCESSFUL, CMD_STATE_FAIL], Dict[str, Any]) -> None
        self.cmdID = cmdID
        self.cmdState = cmdState
        if attributes == None:
            self.attributes = {}    # {'switches':{},'links':{},'servers':{},'vnfis':{}, "sfcisDict":{}}
        else:
            self.attributes = attributes

    def __str__(self):
        string = "{0}\n".format(self.__class__)
        for key,values in self.__dict__.items():
            string = string + "{0}:{1}\n".format(key, values)
        return string

    def __repr__(self):
        return str(self)
