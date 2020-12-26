# 测试用例

收集拓扑信息

收集服务器集信息

部署一条SFCI，NF部署在server和P4交换机上

删除一条SFCI

部署10条SFCI，其中5条NF全都部署在server上，剩余5条NF全都部署在P4交换机上

删除5条SFCI

收集SFCI状态信息，模拟器需要能够汇报：
* SFCI上的每个VNFI的输入输出流量大小(Mbps)
* base/slo.py，其中availability暂时先固定为0.999；latencyBound为模拟出的端到端时延；throughput为模拟计算得到的吞吐量；dropRate为模拟计算得到的丢包率；
