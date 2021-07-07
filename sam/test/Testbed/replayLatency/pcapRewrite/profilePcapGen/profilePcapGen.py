#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.shellProcessor import ShellProcessor


DUT_TYPE_CLASSIFIER = "DUT_TYPE_CLASSIFIER"
DUT_TYPE_SFF = "DUT_TYPE_SFF"


class ProfilePcapGen(object):
    def __init__(self):
        self.sP = ShellProcessor()
        self.newDstIP = "2.2.2.2"
        self.osrcip = "2.2.0.36"
        self.odstip = "10.16.1.1"

    def genPcap(self, filePath, dutType, outFilePath):
        if dutType == DUT_TYPE_CLASSIFIER:
            # tcprewrite --enet-vlan=del --infile=./pcap/univ1_pt20.pcap --outfile=./pcap/univ1_pt20_delVLAN.pcap
            # ./pcapRewrite -f ./pcap/univ1_pt20_delVLAN.pcap -w ./pcap/univ1_pt20_delVLAN_mapDstip.pcap -dstipmap 2.2.2.2
            # tcprewrite -C --fixlen=pad --tos=0 --infile=./pcap/univ1_pt20_delVLAN_mapDstip.pcap --outfile=./pcap/classifierProfiling.pcap
            delVlanFilePath = self.addSuffix(filePath, "_delVLAN")
            self.sP.runShellCommand("tcprewrite --enet-vlan=del " \
                + " --infile=" + filePath \
                + " --outfile=" + delVlanFilePath
            )

            delVlanMapDstIPFilePath = self.addSuffix(delVlanFilePath,
                 "_mapDstIP")
            self.sP.runProcess("../pcapRewrite -f " \
                + delVlanFilePath \
                + " -w " + delVlanMapDstIPFilePath \
                + " -dstipmap " + self.newDstIP)

            self.sP.runProcess(
                "tcprewrite -C --fixlen=pad --tos=0 " \
                + " --infile=" + delVlanMapDstIPFilePath \
                + " --outfile=" + outFilePath
            )

        elif dutType == DUT_TYPE_SFF:
            # tcprewrite -m 1414 --mtu-trunc --enet-vlan=del --infile=./pcap/univ1_pt20.pcap --outfile=./pcap/univ1_pt20_delVLAN.pcap
            # ./pcapRewrite -f ./pcap/univ1_pt20_delVLAN.pcap -w ./pcap/univ1_pt20_delVLAN_mapDstip_oip.pcap -dstipmap 2.2.2.2 -osrcip 2.2.0.36 -odstip 10.16.1.1
            # tcprewrte -C --fixlen=pad --tos=0 --infile=./pcap/univ1_pt20_delVLAN_mapDstip_oip.pcap --outfile=./pcap/sffProfiling.pcap
            delVlanFilePath = self.addSuffix(filePath, "_delVLAN")
            self.sP.runShellCommand("tcprewrite -m 1414 --mtu-trunc --enet-vlan=del " \
                + " --infile=" + filePath \
                + " --outfile=" + delVlanFilePath
            )

            delVlanMapDstIPFilePath = self.addSuffix(delVlanFilePath,
                 "_mapDstIP_oip")
            self.sP.runProcess("../pcapRewrite -f " \
                + delVlanFilePath \
                + " -w " + delVlanMapDstIPFilePath \
                + " -dstipmap " + self.newDstIP + " -osrcip " \
                + self.osrcip + " -odstip " + self.odstip)

            self.sP.runProcess(
                "tcprewrite -C --fixlen=pad --tos=0 " \
                + " --infile=" + delVlanMapDstIPFilePath \
                + " --outfile=" + outFilePath
            )
        else:
            raise ValueError("Unsupport dut type.")

    def addSuffix(self, filePath, suffix):
        index = filePath.find(".pcap")
        if index != -1:
            return filePath[:index] + suffix + filePath[index:]
        else:
            return filePath + suffix


if __name__ == "__main__":
    ppg = ProfilePcapGen()

    ppg.genPcap("../pcap/univ1_pt20.pcap",
        DUT_TYPE_CLASSIFIER, "../pcap/classifierProfiling.pcap")

    ppg.genPcap("../pcap/univ1_pt20.pcap",
        DUT_TYPE_SFF, "../pcap/fwdProfiling.pcap")

    ppg.osrcip = "2.2.0.38"
    ppg.odstip = "10.32.1.1"
    ppg.genPcap("../pcap/univ1_pt20.pcap",
        DUT_TYPE_SFF, "../pcap/fwProfiling.pcap")

    ppg.osrcip = "2.2.0.38"
    ppg.odstip = "10.64.1.1"
    ppg.genPcap("../pcap/univ1_pt20.pcap",
        DUT_TYPE_SFF, "../pcap/monitorProfiling.pcap")

    ppg.osrcip = "2.2.0.38"
    ppg.odstip = "10.80.1.1"
    ppg.genPcap("../pcap/univ1_pt20.pcap",
        DUT_TYPE_SFF, "../pcap/lbProfiling.pcap")

    ppg.osrcip = "2.2.0.38"
    ppg.odstip = "10.112.1.1"
    ppg.genPcap("../pcap/univ1_pt20.pcap",
        DUT_TYPE_SFF, "../pcap/natProfiling.pcap")

    ppg.osrcip = "2.2.0.38"
    ppg.odstip = "10.128.1.1"
    ppg.genPcap("../pcap/univ1_pt20.pcap",
        DUT_TYPE_SFF, "../pcap/vpnProfiling.pcap")
