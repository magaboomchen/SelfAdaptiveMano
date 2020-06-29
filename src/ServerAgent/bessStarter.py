import subprocess
import logging

class BessStarter():
    def __init__(self):
        logging.info('Init bessctl')
        if self.bessctlIsRun() == 0:
            self.startBESSCTL()

    def bessctlIsRun(self):
        out_bytes = subprocess.check_output(["ps -ef | grep bessctl"],shell=True)
        if out_bytes.count("bessctl") > 2:
            logging.info("Bessctl has already running.")
            return 1
        else:
            return 0

    def startBESSCTL(self):
        out_bytes = subprocess.check_output(["sudo $RTE_SDK/../../bessctl/bessctl daemon start"],shell=True)
        logging.info("Start bessctl.")