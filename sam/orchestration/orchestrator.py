#!/usr/bin/env python
import logging

SFC_DOMAIN_PREFIX = "10.0.0.0"
SFC_DOMAIN_PREFIX_LENGTH = 8    # DO NOT MODIFY THIS VALUE, otherwise BESS will incurr error
SFCID_LENGTH = 12   # DO NOT MODIFY THIS VALUE, otherwise BESS will incurr error
VNFID_LENGTH = 4    # DO NOT MODIFY THIS VALUE, otherwise BESS will incurr error
PATHID_LENGTH = 8   # DO NOT MODIFY THIS VALUE, otherwise BESS will incurr error

class Orchestrator(object):
    def __init__(self):
        exit(1)

if __name__=="__main__":
    logging.basicConfig(level=logging.INFO)