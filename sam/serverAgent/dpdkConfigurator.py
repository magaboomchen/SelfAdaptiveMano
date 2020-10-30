#!/usr/bin/python
# -*- coding: UTF-8 -*-

import subprocess

from sam.base.loggerConfigurator import LoggerConfigurator

UNBIND = 0
BIND_IGB_UIO = 1
BIND_OTHER_DRIVER = 2


class DPDKConfigurator(object):
    def __init__(self, NICPCIAddress):
        logConfigur = LoggerConfigurator(__name__, './log',
            'dpdkConfigurator.log', level='info')
        self.logger = logConfigur.getLogger()
        self.logger.info('Config DPDK nic: ' + NICPCIAddress )
        self._NICPCIAddress = NICPCIAddress
        self.configDPDK()

    def configDPDK(self):
        self.insertIGB_UIO()
        status = self.getNICStatus()
        if status == BIND_IGB_UIO:
            pass
        elif status == UNBIND:
            self.bindNIC()
        elif status == BIND_OTHER_DRIVER:
            self.unbindNIC()
            self.bindNIC()
        else:
            self.logger.error("Config DPDK failed.")
            exit(1)

    def insertIGB_UIO(self):
        out_bytes = subprocess.check_output(['lsmod'],shell=True)
        if out_bytes.find('igb_uio') == -1:
            out_bytes = subprocess.check_output(['sudo modprobe uio'],shell=True)
            out_bytes = subprocess.check_output(
                ['sudo insmod $RTE_SDK/build/kmod/igb_uio.ko'],
                shell=True
                )
            self.logger.info("Insert IGB_UIO successfully.")
        else:
            self.logger.info("IGB_UIO already inserted.")

    def getNICStatus(self):
        out_bytes = subprocess.check_output(
            ['sudo python $RTE_SDK/usertools/dpdk-devbind.py --status-dev net | grep ' + self._NICPCIAddress],
             shell=True
            )
        if out_bytes.find('drv=')  == -1:
            return UNBIND
        else:
            out_text = out_bytes.split('drv=')[1].split(' unused=')[0]
            if out_text == 'igb_uio':
                return BIND_IGB_UIO
            else:
                return BIND_OTHER_DRIVER

    def bindNIC(self):
        out_bytes = subprocess.check_output(
            ["sudo python $RTE_SDK/usertools/dpdk-devbind.py --bind=igb_uio " + self._NICPCIAddress],
             shell=True
            )

    def unbindNIC(self):
        out_bytes = subprocess.check_output(
            ["sudo python $RTE_SDK/usertools/dpdk-devbind.py -u " + self._NICPCIAddress],
             shell=True
            )