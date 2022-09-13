#!/usr/bin/python
# -*- coding: UTF-8 -*-

import subprocess

from sam.base.loggerConfigurator import LoggerConfigurator

UNBIND = 0
BIND_IGB_UIO = 1
BIND_I40E = 2
BIND_OTHER_DRIVER = 3


class DPDKConfigurator(object):
    def __init__(self, nicPCIAddress):
        logConfigur = LoggerConfigurator(__name__, './log',
            'dpdkConfigurator.log', level='info')
        self.logger = logConfigur.getLogger()
        self.logger.info('Config DPDK nic: ' + nicPCIAddress )
        self._NICPCIAddress = nicPCIAddress
        self.configDPDK()

    def configDPDK(self):
        self.mount1GBHugepages()
        self.insertIGB_UIO()
        status = self.getNICStatus()
        if status == BIND_IGB_UIO:
            pass
        elif status == UNBIND:
            self.bindNIC()
        elif status == BIND_I40E:
            self.unbindNIC()
            self.bindNIC()
        elif status == BIND_OTHER_DRIVER:
            self.unbindNIC()
            self.bindNIC()
        else:
            self.logger.error("Config DPDK failed.")
            exit(1)

    def mount1GBHugepages(self):
        command = "sudo mkdir -p /mnt/huge_1GB " \
                    + "&& sudo mount -t hugetlbfs -o pagesize=1G none /mnt/huge_1GB " \
                    + "&& sudo mount -t hugetlbfs nodev /mnt/huge_1GB"
        out_bytes = subprocess.check_output(
            [command],
             shell=True
            )

    def insertIGB_UIO(self):
        out_bytes = subprocess.check_output(['lsmod'], shell=True)
        out_bytes = str(out_bytes)
        if out_bytes.find('igb_uio') == -1:
            out_bytes = subprocess.check_output(['sudo modprobe uio'], shell=True)
            out_bytes = subprocess.check_output(
                ['sudo insmod $RTE_SDK/build/kmod/igb_uio.ko'],
                shell=True
                )
            self.logger.info("Insert IGB_UIO successfully.")
        else:
            self.logger.info("IGB_UIO already inserted.")

    def getNICStatus(self):
        out_bytes = subprocess.check_output(
            ['sudo env "PATH=$PATH" python $RTE_SDK/usertools/dpdk-devbind.py --status-dev net | grep ' + self._NICPCIAddress],
             shell=True
            )
        out_bytes = str(out_bytes)
        if out_bytes.find('drv=')  == -1:
            return UNBIND
        else:
            out_text = out_bytes.split('drv=')[1].split(' unused=')[0]
            if out_text == 'igb_uio':
                return BIND_IGB_UIO
            elif out_text == 'i40e':
                return BIND_I40E
            else:
                return BIND_OTHER_DRIVER

    def bindNIC(self):
        out_bytes = subprocess.check_output(
            ['sudo env "PATH=$PATH" python $RTE_SDK/usertools/dpdk-devbind.py --bind=igb_uio ' + self._NICPCIAddress],
             shell=True
            )

    def unbindNIC(self):
        out_bytes = subprocess.check_output(
            ['sudo env "PATH=$PATH" python $RTE_SDK/usertools/dpdk-devbind.py -u ' + self._NICPCIAddress],
             shell=True
            )