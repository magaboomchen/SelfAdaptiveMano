# 测试设置

## 拓扑
测试拓扑为FAT-TREE k=32

0-255为核心交换机的ID

256-767为聚合交换机的ID

768-1279为ToR交换机的ID

10001开始为服务器ID

每个ToR连接20台服务器，
其中一台服务器的种类为SERVER_TYPE_CLASSIFIER，
一台服务器种类为SERVER_TYPE_NORMAL，
剩下的为SERVER_TYPE_NFVI

每个ToR都是P4交换机，可以在其上部署NF

拓扑以pickle的形式存储，simulator直接读取该文件获取拓扑

拓扑pickle文件是一个字典：
```
topologyDict = {
    "nodeNum": self.nodeNum,    # 节点总数
    "linkNum": self.linkNum,    # 链路总数
    "vnfLocation": self.vnfLocation,    # ignore this
    "sfcRequestSourceDst": self.sfcRequestSourceDst,    # ignore this
    "links": self.links,    # 链路集合
    "switches": self.switches,  # 交换机集合
    "servers": self.servers # 服务器集合
}
```

```
self.links[(srcNodeID,dstNodeID)] = {
    'link':Link(srcNodeID, dstNodeID, bandwidth=bw),
    'Active':True,
    'Status':None}
```

```
self.switches[srcNodeID] = {
    'switch': Switch(srcNodeID,
        self._getSwitchType(srcNodeID),
        self._dhcp.genLanNet(srcNodeID),
        self._isSwitchProgrammable(srcNodeID)),
    'Active':True,
    'Status':None}
```

```
self.servers[serverID] = {'Active': True,
            'timestamp': datetime.datetime(2020, 10, 27, 0,
                                            2, 39, 408596),
            'server': server,
            'Status': None}
```


## Command
每个command/commandReply都有一个attributes属性，里面存储了命令的重要信息，以下是部分命令的attributes属性（你可以打印pytest中的command来查看其属性）：

### CMD_TYPE_GET_SERVER_SET
attributes = {'servers': self.serverSet}    # see server.py

### CMD_TYPE_GET_TOPOLOGY
attributes = {
    "switches": self.switches,  # see switch.py
    "links": self.links,    # see link.py
}

### CMD_TYPE_GET_SFCI_STATE
attributes = {
    "vnfis": self.vnfis   # see vnf.py, store state in vnfi.vnfiStatus(Class VNFIStatus)
    "sfci": self.sfci   # see sfc.py, store state in sfci.sloRealTimeValue
}

### CMD_TYPE_GET_FLOW_SET
attributes = {
    "flows": self.flows # see flow.py
}



# 测试用例

* 收集拓扑信息

* 收集服务器集信息

* 部署一条SFCI，NF部署在server和P4上

* 删除一条SFCI

* 收集流信息
    * 每个SFCI可以按照流的下一个服务功能来分成多个截断。比如对于服务链Ingress->Firewall->IDS->Egress来说，该服务功能链实例有3个阶段分别是第0阶段“->Firewall”，第1阶段“->IDS”和第2阶段“->Egress”。
    * 每个SFCI的不同阶段对应着一个流
    * 每个流有一个唯一的标识符，比如对于IPv4的流就是其IPv4目的地址
    * 利用getSFCIFlowIdentifier函数来获取一个SFCI在不同阶段对应的flow的标识符

<!--
*收集SFCI状态信息，模拟器需要能够汇报：
    * SFCI上的每个VNFI的输入输出流量大小(Mbps)存储在VNFIStatus中
    * base/slo.py，其中availability暂时先固定为0.999；latencyBound为模拟出的端到端时延；throughput为模拟计算得到的吞吐量；dropRate为模拟计算得到的丢包率；
-->

# TODO List
SLOMO测量fastclick平台的吞吐量干扰模型
