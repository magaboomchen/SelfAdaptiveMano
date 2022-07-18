# 测试设置

## 拓扑
测试拓扑为FAT-TREE k=32

0-255为核心交换机的ID

256-767为聚合交换机的ID

768-1279为ToR交换机的ID

10001开始为服务器ID

每个ToR连接20台服务器，
其中一台服务器的种类为SERVER_TYPE_CLASSIFIER，
接下来5台的为SERVER_TYPE_NFVI，
最后15台服务器种类为SERVER_TYPE_NORMAL

每台Core Switch都是P4交换机，都是SWITCH_TYPE_DCNGATEWAY
每台ToR都是P4交换机，可以在其上部署NF

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

其中，
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


# Command
每个command/commandReply都有一个attributes属性，里面存储了命令的重要信息，以下是部分命令的attributes属性（你可以打印pytest中的command来查看其属性）：

## CMD_TYPE_GET_SERVER_SET
```
attributes = {
    'servers': servers, # see server.py
    'zone': SIMULATOR_ZONE
}    
```

## CMD_TYPE_GET_TOPOLOGY
```
attributes = {
    "switches": switches,  # see switch.py
    "links": links,    # see link.py
    'zone': SIMULATOR_ZONE
}
```

## CMD_TYPE_GET_SFCI_STATE
```
attributes = {
    "sfcisDict": sfcisDict={sfciID:sfci},   # see sfc.py, store state in sfci.sloRealTimeValue
    'zone': SIMULATOR_ZONE
}
其中，
对于sfci.vnfiSequence中的每个vnfi，其成员变量vnfiStatus是一个VNFIStatus()对象
而VNFIStatus()对象的成员变量state是CMD_TYPE_GET_VNFI_STATE中的contentDict.
```

## [Optional] CMD_TYPE_GET_VNFI_STATE
```
attributes = {
    "vnfisStateDict": vnfisStateDict={vnfiID:contentDict},
    'zone': SIMULATOR_ZONE
}
其中，
contentDict = {
    "vnfType": VNF_TYPE_MONITOR,    # or other type of VNF
    # 下面的为可选key，根据vnfType来选择其中一个即可
    "rateLimitition": 1,            
    "FWRulesNum": 2,
    "FlowStatisticsDict": {
            "ipv4_mon_direction0":{
                "1.1.1.1": 100, # unit: Mbps
                "2.2.2.2": 50   # 生成这些数据即可，仅用于演示
            },
            "ipv4_mon_direction1":{
                "1.1.1.1": 100,
                "2.2.2.2": 50
            },
            "ipv6_mon_direction0":{
                "1.1.1.1": 100,
                "2.2.2.2": 50
            },
            "ipv6_mon_direction1":{
                "1.1.1.1": 100,
                "2.2.2.2": 50
            },
            "rocev1_mon_direction0":{
                "1.1.1.1": 100,
                "2.2.2.2": 50
            },
            "rocev1_mon_direction1":{
                "1.1.1.1": 100,
                "2.2.2.2": 50
            }
        }
}
```

## [Optional] CMD_TYPE_GET_FLOW_SET
```
attributes = {
    "flows": flows, # see flow.py
                        # 其中self.flows是一个list，每个元素是一个sfci在把流量发到vnfID的网络功能时对应的flow对象
                        # flow对象记录了该阶段这个sfci的流量的identifier（网络识别符号，比如目的IPv4地址），以及其流量大小
    'zone': SIMULATOR_ZONE
}
```

# 测试用例

* 收集拓扑信息

* 收集服务器集信息

* 部署一条SFCI，NF部署在server和P4上

* 删除一条SFCI

* 收集SFCI状态信息，模拟器需要能够汇报：
    * SFCI上的每个VNFI的输入输出流量大小(Mbps)存储在VNFIStatus中
    * base/slo.py，其中
        * Availability：uptime/totalTime*100%，返回>99.95%的一个随机数
        * Latency: 端到端时延，可以用performanceModel生成
        * Throughput：端到端吞吐量，根据实时的带宽生成即可
        * Droprate：端到端丢包率，根据吞吐量和分配的带宽，随机生成丢包率：吞吐量小于分配带宽时，丢包率是0~0.1%的随机数；吞吐量大于分配带宽时，就是超过的部分完全丢包来计算丢包数比例 + 0~0.1%的随机数；

* 收集VNFI状态信息，模拟器需要能够汇报：
    * 所有VNFI的state，格式见上述CMD_TYPE_GET_VNFI_STATE

* [Optinal] 收集流信息
    * 每个SFCI可以按照流的下一个服务功能来分成多个阶段。比如对于服务链Ingress->Firewall->IDS->Egress来说，该服务功能链实例有3个阶段分别是第0阶段“->Firewall”，第1阶段“->IDS”和第2阶段“->Egress”。
    * 每个SFCI的不同阶段对应着一个流
    * 每个流有一个唯一的标识符，比如对于IPv4的流就是其IPv4目的地址
    * 利用getSFCIFlowIdentifier函数来获取一个SFCI在不同阶段对应的flow的标识符

## Cautions
* pytest 测试用例的setup没有启动simulator，可以另开terminal启动simulator
