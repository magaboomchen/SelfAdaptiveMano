# 需求
高性能

可以根据dockerController下发的config配置防火墙规则

支持单节点故障保护（Optional）

支持双向的SFC

# 设计
## 高性能
采用dpdk开发

## 可以根据dockerController下发的config配置防火墙规则
实现stateManager，通过gRPC/dockerAPI接收config

## 支持单节点故障保护
为了支持故障保护，可以采用stateless设计：状态信息和计算单元分离。

有两个代表性工作，分别是StatelessNF和Tripod。其中StatelessNF中有一些伪代码可以参考。

[2017][NSDI]Stateless Network Functions: Breaking the Tight Coupling of State and Processing

[2019][JSAC]Tripod: Towards a Scalable, Efficient and Resilient Cloud Gateway

但是他们都无法解决单节点故障问题，即集中式状态所在服务器发生故障。

我们需要复制状态信息，并且保证状态信息全网同步。

设计好API，从local获取流的状态信息，在global修改流的状态信息。

## 双方向SFC
两个端口（连接bess pmdport）负责datapath的输入输出，从不同端口进入表示方向

第三个端口（连接control nic interfaces）负责stateManager之间的同步。

需要支持IPv4 Tunnel的SFC路由，即忽略最外层的IP header。