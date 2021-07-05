#!/usr/bin/python
# -*- coding: UTF-8 -*-

MAIN_TABLE = 0

SOFTWARE_SFF = "SOFTWARE_SFF"
HARDWARE_SFF = "HARDWARE_SFF"

MININET_ENV = "MININET_ENV"
PICA8_ENV = "PICA8_ENV"
PICA8_UFRR_LOGICAL_TWO_TIER_ENV = "PICA8_UFRR_LOGICAL_TWO_TIER_ENV"
CURRENT_ENV = PICA8_UFRR_LOGICAL_TWO_TIER_ENV

DCN_GATEWAY_PEER_ARP = "STATIC"
# DCN_GATEWAY_PEER_ARP = "DYNAMIC"  # please send arp to claim peer switch's mac
DEFAULT_DCN_GATEWAY_PEER_SWITCH_MAC = "90:e2:ba:b1:4d:0e"

ARP_TIMEOUT = 1
ARP_MAX_RETRY_NUM = 10

if CURRENT_ENV == PICA8_UFRR_LOGICAL_TWO_TIER_ENV:
    DEFAULT_DCN_GATEWAY_OUTBOUND_PORT_NUMBER = 49
    DCNGATEWAY_INBOUND_PORT = 49
    SWITCH_CONF_FILEPATH = "./conf/logicalTwoTier.yaml"
    ZONE_NAME = "PICA8_ZONE"

else:
    DEFAULT_DCN_GATEWAY_OUTBOUND_PORT_NUMBER = 1
    DCNGATEWAY_INBOUND_PORT = 1
    SWITCH_CONF_FILEPATH = "./conf/triangle.yaml"
    ZONE_NAME = ""
