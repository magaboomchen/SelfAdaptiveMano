import os
import sys
import subprocess
import logging

class SystemChecker():
    def __init__(self):
        self.checkUserPermission()
        self.checkRTE_SDK()

    def checkUserPermission(self):
        if 'SUDO_UID' in os.environ.keys():
            logging.warning("Check user permission, please don't use sudo or root.")
            sys.exit(1)

    def checkRTE_SDK(self):
        # check whether $RTE_SDK is available
        out_bytes = subprocess.check_output(['echo $RTE_SDK'], shell=True)
        if len(out_bytes) == 1:
            logging.error("Path environment $RTE_SDK is not defined, please define it as the path of dpdk directory.")
            exit(1)