from ruamel import yaml
import sys
from sam.base.socketConverter import SocketConverter

class SwitchConf(object):
    def __init__(self, dpid, switchType, switchID, dcnGatewaySelfIP=None, dcnGatewayPeerIP=None):
        self.dpid = dpid
        self.switchType = switchType
        self.switchID = switchID
        self.lANNet = self._genLANNet(self.dpid)
        self.gatewayIP = self._genSwitchGatewayIP(self.dpid)
        self.dcnGatewayPeerIP = dcnGatewayPeerIP
        self.dcnGatewaySelfIP = dcnGatewaySelfIP

    def setLANNet(self,lanNet):
        self.lANNet = lanNet

    def setGatewayIP(self,gatewayIP):
        self.gatewayIP = gatewayIP

    def _genLANNet(self,dpid):
        switchID = self.switchID & 0x7FF
        net = (2<<24) + (2<<16) + (switchID<<5)
        return SocketConverter().int2ip(net) + "/27"

    def _genSwitchGatewayIP(self,dpid):
        switchID = self.switchID & 0x3FF
        gatewayIP = (2<<24) + (2<<16) + (switchID<<5) + 1
        return SocketConverter().int2ip(gatewayIP)

    def __str__(self):
        return ("dpid:%s\nswitchType:%s\nswitchID:%d\n" 
            %(self.dpid, self.switchType, self.switchID)
        )

class SwitchConfGenerator(object):
    def __init__(self):
        self.switches = {}
        self.yaml = yaml.YAML()
        self.yaml.register_class(SwitchConf)

    def addSwtichTopoConf(self, switch):
        self.switches[switch.dpid] = switch
    
    def delSwitchConf(self, switch):
        del self.switches[switch.dpid]

    def genSwitchConfFile(self, filepath):
        with open(filepath, 'w') as nf:
            self.yaml.dump(self.switches, nf)

if __name__ == '__main__':
    s1 = SwitchConf(0x0000000000000001, "DCNGateway", 1, "1.1.1.1", "1.1.1.2")
    s2 = SwitchConf(0x0000000000000002, "ToR", 2)
    s3 = SwitchConf(0x0000000000000003, "ToR", 3)

    scg = SwitchConfGenerator()
    scg.addSwtichTopoConf(s1)
    scg.addSwtichTopoConf(s3)
    scg.addSwtichTopoConf(s2)

    scg.genSwitchConfFile("./switch.yaml")