#!/usr/bin/python
# -*- coding: UTF-8 -*-

# if user doesn't assign mapping algorithm, use default mapping algorithm
DEFAULT_MAPPING_TYPE = "MAPPING_TYPE_MMLPSFC"

# bottom control system
if DEFAULT_MAPPING_TYPE == "MAPPING_TYPE_NETSOLVER_ILP":
    BATCH_SIZE = 100
    BATCH_TIMEOUT = 99999999
elif DEFAULT_MAPPING_TYPE == "MAPPING_TYPE_NETPACK":   
    BATCH_SIZE = 100
    BATCH_TIMEOUT = 3
    # In testbed_sw1 instance, BATCH_SIZE = 5
elif DEFAULT_MAPPING_TYPE == "MAPPING_TYPE_NONE":
    BATCH_SIZE = 1
    BATCH_TIMEOUT = 1
else:
    BATCH_SIZE = 100
    BATCH_TIMEOUT = 3

MAX_SFC_LENGTH = 7
RE_INIT_TABLE = True    # Please disable this when presenting after clean up all mysql data.
ENABLE_OIB = True  # Please enable this in final results.

# whether use existed vnfi
VNFI_ASSIGN_MODE = True


ENABLE_INGRESS_EGRESS_GENERATION = False    # for TXXB test

ENABLE_PREFERRED_DEVICE_SELECTION = True