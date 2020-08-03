import subprocess
import logging
import psutil

class BessStarter(object):
    def __init__(self):
        logging.info('Init bessd')
        if self.isBessdRun() == 0:
            self.startBESSD()

    def startBESSD(self):
        out_bytes = subprocess.check_output(["sudo $RTE_SDK/../../bessctl/bessctl daemon start"],shell=True)
        logging.info("Start bessd.")

    def isBessdRun(self):
        for p in psutil.process_iter(attrs=['pid', 'name']):
            if 'bessd' in p.info['name']:
                logging.info("bessd has already running.")
                return True
        return False