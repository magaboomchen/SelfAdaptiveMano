# 开发建议

simulator的开发可能会用到/sam/base，/sam/measurement/dcnInfoBaseMaintainer以及sam/orchestration/algorithms/base/performanceModel中的很多类。
开发时请复用这些类。
增加新功能时请继承这些类然后再开发新功能。

## 使用说明
### 如何启动
```shell
python sam/simulator/simulator.py
```
启动时会默认执行`sam/simulator/simulator_init`文件中的命令。
如果需要修改rabbitMQ的配置，请修改`sam/base/rabbitMQConf.json`，`MessageAgent.setRabbitMqServer`方法无法改变连接时的配置（暂不知道是有意的设计还是bug）。

### 命令说明
1. 清除全部拓扑数据。
```
reset
```
2. 载入拓扑数据。
```
load filename
```
3. 模拟服务器的正常与故障状态。
```
server server_id up|down
```
4. 模拟交换机的正常与故障状态。
```
switch switch_id up|down
```
5. 模拟链路的正常与故障状态。
```
link src_id dst_id up|down
```
7. 为sfci添加一条traffic，默认流量为常量，pktSize为500。
```
add|del traffic_id sfci_id dir_id --trafficRate=<value in Mbps>
```
8. 修改traffic的流量为常量
```
traffic traffic_id --trafficPattern=constant --value=<value> [--pktSize=<pkt size>]
```
9. 修改traffic的流量为均匀分布的随机变量
```
traffic traffic_id --trafficPattern=uniform --min=<min> --max=<max> [--pktSize=<pkt size>]
```
10. 模拟对server的资源的使用（静态）
```
server server_id cpu|mem --pattern=constant --value=<value>
```
11. 模拟对server的资源的使用（均匀分布）
```
server server_id cpu|mem --pattern=uniform --min=<value> --max=<value>
```
> 注： 上述两条命令中value的单位，cpu为百分比（%），内存为MB。

### 可定义参数
在 [simulatorInfoBaseMaintainer.py](./simulatorInfoBaseMaintainer.py) 中有两个参数，
其中`MAX_BG_BW`表示背景流量最大带宽，背景流量的带宽将在大于0和小于该值的范围内随机生成。
`CHECK_CONNECTIVITY`表示更新背景流量时是否检查路径的连通性。
