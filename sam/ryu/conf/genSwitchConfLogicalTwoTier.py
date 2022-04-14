#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.ryu.conf.switchConfGenerator import SwitchConf


if __name__ == '__main__':
    s1 = SwitchConf(0x0000000000000001, "SWITCH_TYPE_DCNGATEWAY", 1, "1.1.1.1", "1.1.1.2",
                    physicalSwitchManagementIP="192.168.100.1",
                    physicalSwitchUserName="admin",
                    physicalSwitchPassword="thu325325")
    s2 = SwitchConf(0x0000000000000002, "SWITCH_TYPE_NPOP", 2, physicalSwitchManagementIP="192.168.100.2",
                    physicalSwitchUserName="admin",
                    physicalSwitchPassword="thu325325")
    s3 = SwitchConf(0x0000000000000003, "SWITCH_TYPE_NPOP", 3, physicalSwitchManagementIP="192.168.100.2",
                    physicalSwitchUserName="admin",
                    physicalSwitchPassword="thu325325")
    s4 = SwitchConf(0x0000000000000004, "SWITCH_TYPE_FORWARD", 4, physicalSwitchManagementIP="192.168.100.2",
                    physicalSwitchUserName="admin",
                    physicalSwitchPassword="thu325325")
    s5 = SwitchConf(0x0000000000000005, "SWITCH_TYPE_FORWARD", 5, physicalSwitchManagementIP="192.168.100.1",
                    physicalSwitchUserName="admin",
                    physicalSwitchPassword="thu325325")
    s6 = SwitchConf(0x0000000000000006, "SWITCH_TYPE_FORWARD", 6, physicalSwitchManagementIP="192.168.100.1",
                    physicalSwitchUserName="admin",
                    physicalSwitchPassword="thu325325")

    scg = SwitchConfGenerator()
    scg.addSwtichTopoConf(s1)
    scg.addSwtichTopoConf(s2)
    scg.addSwtichTopoConf(s3)
    scg.addSwtichTopoConf(s4)
    scg.addSwtichTopoConf(s5)
    scg.addSwtichTopoConf(s6)

    scg.genSwitchConfFile("./logicalTwoTier.yaml")


