# Command
每个command/commandReply都有一个attributes属性，里面存储了命令的重要信息，以下是部分命令的attributes属性（你可以打印pytest中的command来查看其属性）：

## CMD_TYPE_ADD_SFC
* sfc = attributes['sfc'] # type: class SFC
* 将双向的acl表项部署到turbonet中指定的ingress switch上(一般是DCN_GATEWAY)
* 调用wrh提供的下发分类器规则的API;
    * ingress：下发direction['match]，action是封装一个NSH header
    * egress: 下发一个规则match NSH header(SPI,SI), action是解封装

## CMD_TYPE_ADD_SFCI
* sfc = attributes['sfc'] # type: class SFC
* sfci = attributes['sfci'] # type: class SFCI
* 调用wrh提供的下发NSH路由规则的API
* SPI即SFCIID
* 路由模态可以从SFC和SFCI中获取（同一个SFC下的所有SFCI路由模态相同）

## CMD_TYPE_DEL_SFCI
* sfc = attributes['sfc'] # type: class SFC
* sfci = attributes['sfci'] # type: class SFCI
* 调用wrh提供的删除NSH路由规则的API

## CMD_TYPE_DEL_SFC
* sfc = attributes['sfc'] # type: class SFC
* 将双向的acl表项部署到turbonet中指定的ingress switch上(一般是DCN_GATEWAY)
* 调用wrh提供的删除分类器规则的API

## CMD_TYPE_GET_SFCI_STATE
```
attributes = {
    "sfcisDict": sfcisDict={sfciID:sfci},   # see sfc.py, store state in sfci.sloRealTimeValue
    'zone': TURBONET_ZONE
}
```

# 测试用例

* 部署3条SFCI，所有NF部署在P4上

* 删除3条已经部署的SFCI

* 收集SFCI状态信息，模拟器需要能够汇报：
    * SFCI上的每个VNFI的输入输出流量大小(Mbps)存储在VNFIStatus中
    * base/slo.py，其中
        * Availability：uptime/totalTime*100%，返回>99.95%的一个随机数
        * Latency: 端到端时延，可以用performanceModel生成
        * Throughput：端到端吞吐量，根据实时的带宽生成即可
        * Droprate：端到端丢包率，根据吞吐量和分配的带宽，随机生成丢包率：吞吐量小于分配带宽时，丢包率是0~0.1%的随机数；吞吐量大于分配带宽时，就是超过的部分完全丢包来计算丢包数比例 + 0~0.1%的随机数；

## Cautions
* pytest 测试用例的setup没有启动p4Controller，可以另开terminal启动p4Controller
