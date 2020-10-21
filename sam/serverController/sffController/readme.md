SFC一共有两个方向：方向0和方向1，默认流量走方向0.

每个VNF有两个PMDPort，分别是PMDPort0和PMDPort1.

每个PMDPort有QueueInc和QueueOut两个队列，分别是入口队列和出口队列。

```
PMDPort0对应的队列名称为：QueueInc1,QueueOut0
PMDPort1对应的队列名称为：QueueInc0,QueueOut1
```

```
方向0：从PMDPort0的QueueOut0进入VNF，然后VNF把pkt从PMDPort1的QueueInc0发进BESS；
方向1：从PMDPort1的QueueOut1进入VNF，然后VNF把pkt从PMDPort0的QueueInc1发进BESS；
```