# TODO list
## 把前端的标题替换为项目课题名称

## 安装SAM
根据sam/INSTALL.md来安装

## 数据展示（静态数据->动态数据）
### DB: Dashboard
* CloudUser List
    * [done]ID, USER_NAME, USER_UUID, USER_TYPE
* Zone List
    * [done]ID, ZONE_NAME
* RoutingMorphic List
    * [done]ID, ROUTING_MORPHIC_NAME
### DB: Measurer
* Server List
    * [done]ID, ZONE_NAME, SERVER_ID, IPV4, CPU_UTILIZATION
* Switch List
    * [done]ID, ZONE_NAME, SWITCH_ID
* Link List
    * [done]ID, SRC_ID, DST_ID, BANDWIDTH, UTILIZATION
### DB: Orchestrator
* Request List
    * [done]ID, REQUEST_UUID, REQUEST_TYPE, SFC_UUID, STATE
* SFC List
    * [done]ID, ZONE_NAME, SFC_UUID, SFCIID_LIST, STATE
* SFCI List
    * [done]ID, SFCIID, VNFI_UUID_LIST, STATE, ORCHESTRATION_TIME(编排部署时间)
    * FORWARDING_PATH: 1->2->3
* VNFI List (用test_sfci.py测试)
    * [done]ID, VNFI_UUID, VNFI_TYPE
    * VNFI_STATE: NORMAL/ABNORMAL/OVERLOAD

### 提供需要展示的数据
* 在ppt中列出需要展示的数据实例
* 实现XXXInfoBaseMaintainer来承载不同的数据
* 实现unit test
    * 通过调用不同的XXXInfoBaseMaintainer：
        * [done]清空数据库Tables
        * [done]将需要展示的数据存入数据库中

## 添加请求
* 添加SFC
    * 显示已有的SFC
    * 选择业务类型（appType）
        * 高带宽（"highBW"），低时延（"lowDelay"），高可用（"HighAvaiablity"），尽力而为（"bestEffort"）
    * 输入SFC信息（sfcInfo）
        * VNF顺序（vnfSeq）
            * 类型（vnfType）：VNF_TYPE_FW，VNF_TYPE_NAT, VNF_TYPE_LB, VNF_TYPE_MONITOR, VNF_TYPE_RATELIMITER
            * 配置规则（config）：租户输入一段文字
        * 扩缩容模式（scalingMode）
            * 自动（"Auto"），手动（"Manual"）
    * 选择路由模态（routingMorphic）
        * "IPv4"，"IPv6"，"SRv6", "RecoV1"
    * 选择VNF的设备模态（deviceMorphic）
        * "auto"，"P4"，"x86"
* 添加SFCI
    * 显示已有的SFCI
    * 按钮添加SFCI
* 删除SFCI
    * 显示已有的SFCI
    * 按钮删除SFCI
* 删除SFC
    * 显示已有的SFC
    * 按钮添加SFC

## 符合审美的数据展示
* 基于echart实现多样化的数据展示
