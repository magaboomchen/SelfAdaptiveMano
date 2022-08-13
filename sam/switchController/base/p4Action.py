#!/usr/bin/python
# -*- coding: UTF-8 -*-

from typing import List, Union

ACTION_TYPE_FORWARD = "ACTION_TYPE_FORWARD"
ACTION_TYPE_ENCAPSULATION_NSH = "ACTION_TYPE_ENCAPSULATION_NSH"
ACTION_TYPE_DECAPSULATION_NSH = "ACTION_TYPE_DECAPSULATION_NSH"

FIELD_TYPE_SPI = "FIELD_TYPE_SPI"
FIELD_TYPE_SI = "FIELD_TYPE_SI"
FIELD_TYPE_NEXT_PROTOCOL = "FIELD_TYPE_NEXT_PROTOCOL"
FIELD_TYPE_MDTYPE = "FIELD_TYPE_MDTYPE"
FIELD_TYPE_ETHERTYPE = "FIELD_TYPE_ETHERTYPE"


class FieldValuePair(object):
    def __init__(self,
                 field, # type: Union[FIELD_TYPE_SPI, FIELD_TYPE_SI, FIELD_TYPE_NEXT_PROTOCOL, FIELD_TYPE_MDTYPE]
                 value  # type: int
                 ):
        self.field = field
        self.value = value


class P4Action(object):
    def __init__(self,
                 actionType,   # type: Union[ACTION_TYPE_FORWARD, ACTION_TYPE_ENCAPSULATION_NSH, ACTION_TYPE_DECAPSULATION_NSH]
                 nextNodeID,   # type: int
                 newFieldValueList=None     # type: List[FieldValuePair]
                 ):
        self.actionType = actionType
        self.nextNodeID = nextNodeID
        self.newFieldValueList = newFieldValueList
