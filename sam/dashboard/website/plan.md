# TODO list
## 把前端的标题替换为项目课题名称

## 安装SAM
根据sam/INSTALL.md来安装

## 数据展示（静态数据->动态数据）
* CloudUser List
    * ID, USER_NAME, USER_UUID, USER_TYPE
* Zone List
    * ID, ZONE_NAME
* RoutingMorphic List
    * ID, ROUTING_MORPHIC_NAME
* Server List
    * ID, ZONE_NAME, SERVER_ID, IPV4, CPU_UTILIZATION
* Switch List
    * ID, ZONE_NAME, SWITCH_ID
* Link List
    * ID, SRC_ID, DST_ID, BANDWIDTH, UTILIZATION
* Request List
    * ID, REQUEST_UUID, REQUEST_TYPE, SFC_UUID, STATE
* SFC List
    * ID, ZONE_NAME, SFC_UUID, SFCIID_LIST, STATE
* SFCI List
    * ID, SFCIID, VNFI_LIST, STATE, ORCHESTRATION_TIME(编排部署时间)
    * FORWARDING_PATH: 1->2->3
* VNFI List (用test_sfci.py测试)
    * ID, VNFI_UUID, VNFI_TYPE
    * VNF_STATE: NORMAL/ABNORMAL/OVERLOAD

### 提供需要展示的数据
* 在ppt中列出需要展示的数据实例
* 实现XXXInfoBaseMaintainer来承载不同的数据
* 实现unit test
    * 通过调用不同的XXXInfoBaseMaintainer：
        * 清空数据库Tables
        * 将需要展示的数据存入数据库中

## 添加请求
* 添加路由模态
    * 路由模态名称
    * 报头长度
    * 匹配域列表：[(offset,bytes), (offset,bytes),...]
* 添加SFC
    * 选择业务类型
        * 高带宽，低时延，高可用，尽力而为
    * 添加SFC
        * VNF顺序
        * 扩缩容模式
        * 自动，手动
    * 选择路由模态
        * IPv4，IPv6，NDN，自定义1，自定义2等等
    * 选择VNF的设备模态
        * 自动（由程序自动选择），P4，x86
* 添加SFCI
* 删除SFCI
* 删除SFC

## 符合审美的数据展示[选做]
* 基于echart实现多样化的数据展示
