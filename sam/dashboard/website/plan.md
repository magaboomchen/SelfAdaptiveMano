# TODO list
## 把前端的标题替换为项目课题名称

## 安装SAM
根据sam/INSTALL.md来安装

## 数据展示（静态数据->动态数据）
* 用户列表
    * 用户名，uuid
* zone列表
    * zone_name, zone_id
* 服务器列表
    * zone_name, 服务器id，ip地址（其他路由模态识别符），CPU利用率
* 交换机列表
    * zone_name, 交换机id，邻居交换机id list，链路状态信息（流量大小）
* SFC列表
    * zone_name, SFC uuid，用户id
* SFCI列表
    * VNF Sequence，逻辑转发路径，路径长度，编排部署时间
        * 路径：A->B->C； 路径长度：3； 编排部署时间：10s
    * SFCI服务质量状态：正常，超载，故障
    * 正常运行的SFCI比例
* VNFI列表
    * zone_name, VNFI uuid，VNFI种类
* Request列表
    * 每个Request所属的user，部署状态, zone_name

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

## 符合审美的数据展示
* 基于echart实现多样化的数据展示
