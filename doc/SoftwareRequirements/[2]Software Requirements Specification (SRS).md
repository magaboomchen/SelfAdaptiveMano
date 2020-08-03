# 软件需求规格说明（TODO）

## 一、概要

### 1.1 目的

通过本文档定义NFV编排和管理系统的需求，以求在项目组员与相关成员之间达成一致的需求描述。

### 1.2 背景

描述系统产生的背景，包括：

a．需开发的软件系统的名称为自适应管理和网络编排系统（Self Adaptive Management and Network Orchestration, SAM）；

b．开发者：张雨轩、陈浩

c．软件系统应用范围：数据中心（Data Center Network, DCN）

d. 用户：DCN的运维人员

e．产生该系统需求的原因或起源

在Internet中，除了负责转发数据包的路由器以外，还有很多负责处理数据包的中间件（Middelbox），比如防火墙，NAT，负载均衡器等等。
在传统的网络中，中间件都是专用设备，我们称其为硬件中间件。
它们采用ASIC实现对数据包的处理，而且必须被放置在流量的闭经之路上，比如放置在网络出入口。

然而，由于硬件中间件价格昂贵，升级困难，部署不灵活，运营商共同提出了网络功能虚拟化技术（Network Function Virtualization, NFV）。
NFV意在使用通用硬件比如x86服务器，将中间件软件化，并运行在虚拟机或者容器中。我们称其为虚拟网络功能（Virtual Network Function, VNF）。

随着NFV的出现，数据中心将很多中间件软件化，比如阿里巴巴对外销售的都是VNF。
在阿里巴巴的数据中心内，一组cluster上跑一类VNF，不同的租户的VNF可以共享同一台服务器。

有时候，租户不仅仅需要一个VNF。
租户可能需要多个VNF按顺序组成服务功能链（Service Function Chain, SFC）来满足其需求。
比如，一个数据中心中典型的SFC为：VPN->Monitor->Firewall->LoadBalance。

近年来越来越多的公有云平台开始提供SFC服务，越来越多的租户为了节省运维开销，开始将SFC外包给公有云[21][41]。
在SFC服务模式中，租户向公有云提交SFC请求，而运维人员负责利用NFV管理和编排系统，对这些SFC请求进行编排和部署。
编排SFC包括决策VNF的实例数量，建立VNF与服务器的映射关系，计算SFC的转发路径。
部署SFC包括根据编排的结果在指定的服务器上启动对应VNF镜像，下发流表实现SFC转发。

然而，租户对VNF的需求越来越大，对这些VNF进行编排和管理变得越来越困难。
随着租户对SFC服务要求的提高，运维人员面临着很多挑战：

1. 租户的数量越来越多，其流量也越来越大，DCN网络服务功能链需要有极高的处理能力

2. 租户要求SFC能够应对基础设施故障，具有故障保护能力和故障恢复能力

3. 租户要求SFC能够应对流量的动态变化，具有快速扩展能力

4. 不同的租户会提出不同的SLA要求，例如可用性、时延、吞吐量要求

如何满足租户的各种要求成为了NFV编排管理系统需要解决的首要问题。

已有一些工作实现了数据中心级别的SFC编排部署。

工业界的Tacker、ONAP、Open Baton等可以实现基本的SFC编排部署功能以及VNF扩缩容和VNF故障恢复功能，但是他们缺乏对租户SLA的考虑。
除此以外，他们不支持SFC的故障保护。

学术界的Stratos[6]提出了一个NFV编排管理系统，它具备流量工程、placement、水平扩展策略等功能。可以满足SFC的正确路由，支持用户SLO，支持1k的SFC扩展。
OpenBox[7]提供了一个网络功能的开发设计管理架构，它支持网络功能的组件划分式部署。
Apple[1]提出了一种NFV编排结构，它支持基本的SFC编排部署同时不干扰其他流量。
HYPER[8]提出了一个支持混合基础设施的NFV管理框架，它的数据平面支持erver和FPGA硬件；它支持流迁移，并在部署VNF时考虑租户SLA。
Daisy[3]实现了除基本SFC编排部署功能以外的功能包括增加/删除/升级VNF等。
Daisy的编排器可以满足租户的SLA要求。
不幸的是，已上工作均未考虑故障保护以及故障恢复功能。
Medhat等人[2]在Open Baton的基础上增加了VNF故障恢复的功能，但是该系统并未考虑SFC的快速扩缩容功能。

在这项工作中，我们尝试解决数据中心级别的SFC高弹性快速扩展编排部署问题。我们要设计并实现一个NFV编排管理系统SelfAdaptiveMano (SAM)，它可以支持：

1. 高性能的流分类：数据中心入口处100Gbps的包分类以及封装能力（可以基于P4实现，也可以基于高性能服务器实现）(接下来的工作还需要咨询一下孙晨师兄，阿里巴巴的VNF如何实现租户流量的包分类？)

2. SFC的故障保护：单节点故障保护率100%

3. SFC的故障恢复：故障恢复时间低于10s（大规模故障比如多个ToR故障，导致主备VNF同时失效，同时影响了大量的SFC，能否在短时间内全部恢复？）[4][5]

4. SFC的快速扩展：SFC垂直扩展时间低于1s，SFC水平扩展时间低于10s（对于10k台服务器的数据中心，能否做到所有SFC同时扩展，扩展时间低于10s？）

5. 满足租户的各种SLA要求，包括可用性、时延、吞吐量要求

SAM的初步系统实现方案：

1. 利用快速重路由技术实现对SFC的故障保护

2. 利用SDN技术和docker容器编排系统实现VNF的故障恢复

3. 利用容器技术实现SFC的快速扩展

4. 通过设计统一编排部署算法API接口，满足不同租户的各种SLA要求

### 1.3 术语

### 1.4 预期读者与阅读建议

| 预期读者      | 阅读建议        |
| :----------- |:------------   |
|系统设计人员   |仔细阅读全部内容。|
|系统实现人员   |仔细阅读全部内容。|

### 1.5 参考资料以及培训材料

Kubernets权威指南（第四版）

Ryu官网指南 <https://pypi.org/project/ryu/>

### 1.6 需求描述约定

#### 功能描述方法

本文档从以下几个方面对功能需求进行描述：

a.业务定义/描述。

b.适用的用户类型

c.业务规则/业务要素。

d.输入：提供所有与本功能有关的输入描述，包括：输入数据类型、媒体、格式、数值范围、精度、单位等。

e.输出：提供与本功能有关所有输出的描述，包括：输出数据类型、方式、格式、精度、单位等，以及图形或显示报告的描述。

f.业务操作流程

g.描述正常业务流程，列举异常情况和处理流程。建议使用图示，并配合必要的文字说明

h.约束条件/特殊考虑

列出在各个工作领域不需计算机化的功能并提供其原因以及特殊条件。

#### 界面描述规则

界面描述使用VISIO的界面模型进行描述。

## 二、项目概述

### 2.1 系统功能

软件系统必须具备的功能及性能、其特征和必须遵守的约束

#### 必备功能

1. 根据SFC请求，将所需的VNF部署到服务器上，租户的流量从服务器发送出后必须按SFC的顺序经过每种VNF，最后送达目的主机

2. 数据中心单节点故障（除了租户所在主机以及控制器所在主机）不影响租户的正常业务

3. 租户流量变大时，可以采用垂直/横向扩展承载增大的流量

4. 首要VNF所在节点故障后，可以自动将首要VNF迁移到指定节点

5. 可以实时查看每个SFC的状态信息和SLO

#### 必要性能

1. 单节点故障保护率100%

2. 垂直扩展时间低于1s

3. 横向扩展时间低于10s

4. 人为蓄意扰动抑制成功率>95%

### 2.2 业务描述

参阅本文档的“背景”章节

### 2.3 数据流程描述（可选）

暂无

### 2.4 用户的特点以及场景

参阅User Requirement

### 2.5 运行环境要求

Linux服务器，openflow交换机

### 2.6 设计和实现上的限制

SFC的入口ingress为classifier，egress负责decap。

逻辑上，只有用户的egress数量为1时，才能够计算最短路径。

因此我们限定用户的egress数量为1，可以将classifier承担ingress和egress的功能。

## 三、功能需求的描述

参阅User Requirement

## 四、非功能需求

参阅User Requirement

### 4.1 系统性能要求

参阅User Requirement

### 五、外部接口说明

### 1. BESSController-Server Controller interfaces

通过gRPC控制server上的BESS
通过dockerAPI远程控制server上的VNF

### 2. RyuApp-Network Controller interfaces

通过RabbitMQ控制openflow Switches

### 3. backend-Database interface

各个模块与VNF和DCN信息库的接口的sql远程操作

### 六、其他需求

暂无

### 七、需求变更识别

### 八、功能列表

### 九、附录

#### 附录一 估算日程安排、工作量和资源

NFV管理和编排系统可以分为前端（提交SFC编排请求、查看SFC服务等级指标、提交SFC删除请求）、后端（SFC编排、VNF库维护、SFC删除、SFC自适应扩缩容/故障恢复）、网络监控控制（获取VNF/server、转发路径、网络拓扑信息，维护DCN信息库、编写SDN控制器应用）三大部分：

1. 前端部分需要自定义好需要展示的界面信息(可以参考Openstack Tacker的代码进行设计和实施)。定义VNF库和DCN数据库中的数据格式后，工作量预估在 1k LoC。

2. 后端部分自己开发，工作量预估在5k LoC（有现实参考，有人自己用python写过调用docker接口实现CRUD功能，代码量不到3k LoC）。（在tacker的基础上增加/修改代码的可行性较差，因为目前的tacker还很不稳定，安装过程遇到很多bug；而且Tacker默认支持的SDN控制器是opendaylight，太重量级了比较难上手；不如自己开发MANO）

3. 网络监控控制部分自己开发，工作量预估在1k LoC。（可以利用服务器控制器的资源监控接口）

#### 附录二 分工

需要安排2个人，前端+网络监控控制部分由一个人实现。后端部分由一个人实现。

明确开发的产品

NFV管理和编排系统

明确交付的产品

NFV管理和编排系统

#### 附录三 工业界已有的编排系统Tacker的代码量

##### Tacker

最小化安装，即tacker+所需的组件（比如horizon、keystone、networking-sfc、kuryr-k8s、tacker-horizon）：需要700k LoC Python

1. tacker文件夹：33k LoC Python、12k LoC YAML

2. tacker-horizon文件夹：3k LoC Python、12k LoC YAML

3. networking-sfc文件夹：28k LoC Python、12k LoC YAML

##### Intel vhost cni

1. go：3220440 LoC

2. HTML:287961 LoC

3. Bourne Shell：27310 LoC

##### Antrea cni

1. go：24874 LoC

2. YAML：1579 LoC

#### 附录四 实验平台

1. master node （运行NFV管理和编排系统、DCN信息库、Server Controller、Network Controller）

    - 服务器(192.168.0.194)：ssh 166.111.68.231 -p 60194; user: smith; code: 123456

2. work node （Server、Software Router）
    - master node上已经配置好两台KVM虚拟机作为work node，均已安装BESS

    - 服务器(192.168.0.173)： user:server0 code:123456

3. SDN switch
    - 实验室小机房有2台，但是暂时还没去借，可以用OvS代替

#### 附录五 参考文献

[1][2016][ICDCS]An NFV Orchestration Framework for Interference-Free Policy Enforcement

[2][2016][SDN-NFV]Resilient orchestration of Service Functions Chains in a NFV environment

[3][2018][ANCS]VNF Chain Allocation and Management at Data Center Scale

[4][2018][jcrd]网络功能虚拟化环境下安全服务链故障的备份恢复机制

[5][2018][NSDI]Andromeda: Performance, Isolation, and Velocity at Scale in Cloud Network Virtualizatione

[6][2013][arXiv]Stratos: A Network-Aware Orchestration Layer for Virtual Middleboxes in Clouds 

[7][2016][SIGCOMM]OpenBox: A software-defined framework for developing, deploying, and managing network functions

[8][2017][JSAC]HYPER A Hybrid High-Performance Framework for Network Function Virtualization

[21][2016][NSDI] Embark: Securely Outsourcing Middleboxes to the Cloud

[41][2012][SIGCOMM] Making Middleboxes Someone else’s Problem: Network Processing As a Cloud Service