- [x] 加载、重制拓扑功能
- [x] 模拟服务器、交换机、链路故障功能
- [x] 添加流量功能
- [x] 模拟流量变化功能

### 2022/04/09 - 2022/04/13

- [x] 读取拓扑性能优化
- [x] 保存命令
- [x] 退出命令
- [x] 增加、删除SFCI时更新链路的占用率
- [x] 增加、删除SFCI时更新服务器CPU与内存的占用率

### 2022/04/14 - 2022/04/20
- [x] 模拟背景流量
- [x] 模拟背景应用资源占用

### 2022/04/20 - 2022/04/27
- [x] server类添加coreUtilization以及hugePageFree的setter
- [x] 更新背景流量时检查交换机以及链路是否故障

### 2022/04/28 - 2022/05/03
- [x] 优化背景流量的更新速度，目前可以在0.2秒以内完成一次完整的更新
- [x] 修改拓扑结构，把部分服务器由NFVI类型改为NORMAL类型
- [x] 一定程度上降低代码的耦合度
