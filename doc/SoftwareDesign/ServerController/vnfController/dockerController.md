# 开发说明
大部分软件已经安装。

开发前请阅读此部分。

我们要开发vnfController，它的功能是根据mediator发出的ADD_SFCI_CMD，在指定的server上安装/配置/删除指定种类的VNF。

每个VNF都是DPDK开发的，需要运行在docker中进行隔离。

每个docker有两个端口，和BESS分配的两个端口连接。

BESS分配的端口是/tmp文件夹下紫色的文件vsock_XXX

PS：

1）虚拟机192.168.0.150和192.168.0.156用于开发/测试vnfController

2）192.168.0.150运行vnfController，这台机器不能跑bess，因为内存只有512MB

3）192.168.0.156运行bess和vnf，这台机器可以跑bess，但是最多只能放置一个VNF，内存4.5GB

4）拓扑参考pptx



# 人工部署VNF
下面是人工实现部署VNF的过程：

1）在虚拟机（192.168.0.156）中启动docker，并运行DPDK程序testpmd。

1.1）启动docker：

    sudo docker run -ti --rm --privileged  --name=test \
    -v /mnt/huge_1GB:/dev/hugepages \
    -v /tmp/:/tmp/  \
    dpdk-app-testpmd

1.2）在docker中运行testpmd：

    ./x86_64-native-linuxapp-gcc/app/testpmd -l 0-1 -n 1 -m 1024 --no-pci \
    --vdev=net_virtio_user0,path=/tmp/vsock0_FW1 \
    --vdev=net_virtio_user0,path=/tmp/vsock1_FW1 \
    --file-prefix=virtio --log-level=8 -- \
    --txqflags=0xf00 --disable-hw-vlan --forward-mode=io --port-topology=chained --total-num-mbufs=2048 -a



# 人工部署VNF命令中参数的提供方式

## （1） msg提供的参数

msg中的vnfi实例提供了很多参数。

### VNFType

具体的有VNF_TYPE_FORWARD，VNF_TYPE_FW等等。

VNF_TYPE_FORWARD表示部署testpmd程序的容器。
命令中dpdk-app-testpmd是testpmd程序的容器镜像名称。

其他类型的VNF需要自己实现，可以通过修改iofwd.c来实现各种vnf。
实现完的vnf需要打包成容器镜像，具体方法可以查看后文。

### VNFIID

本质是一个uuid1，这个VNFIID用于生成命令中的path=/tmp/vsock0_FW1参数。生成方法参考后文。

PS：注意VNFIID不是VNFID

### config

这个是VNF的规则配置，比如对于防火墙，就是ACL表。具体格式未定。

### 未加入的参数

有一些重要的参数（-l 0-1 -m 1024）被遗漏了.

下一次commit会再class VNFI中增加CPU使用数量和Mem使用大小等成员变量，如下：

```
class VNFI(object):
    def __init__(self, ......):
        ......
        self.minCPUNum = 2
        self.maxCPUNum = 2
        self.minMem = 1024
        self.maxMem = 1024
```

vnfController按照max去分配资源即可。（之所以有min和max的区别是因为可能要实现垂直扩展，但是貌似也可以不做，所以这里就先这么设计了。）

## （2） vnfController维护的参数（非固定）

以下参数不是固定参数，要保证不同的VNFI的相应参数不同（用于区分不同的VNFI）

可以用VNFIID来区分。

### --name=XXX
### --vdev=XXX

## （3） 固定参数

其他未提及的参数均为固定参数


# vnfController部署VNF
我们要用程序替代人工部署VNF，所以要开发vnfController。

基于dockerAPI开发： https://docker-py.readthedocs.io/en/stable/

## PS
vnfController部署VNF与人工部署的区别：

在步骤1.2）在vnf中运行testpmd命令

    ./x86_64-native-linuxapp-gcc/app/testpmd -m 1024 --no-pci \
    --vdev=net_virtio_user0,path=/tmp/vsock0_FW1 \
    --vdev=net_virtio_user0,path=/tmp/vsock1_FW1 \
    --file-prefix=virtio --log-level=8 -- \
    --txqflags=0xf00 --disable-hw-vlan --forward-mode=io --port-topology=chained --total-num-mbufs=2048 -a

这里的path=/tmp/vsock0_FW1和path=/tmp/vsock1_FW1需要根据vnfCmd来生成。

生成方法：
vnfCmd中给出了每个VNF的UUID。

这个vdev中的iface=/tmp/vsockX_XXX就是上面命令中path字段的内容。



# test_vnfControllerAddSFCI
有一个测试类test_vnfControllerAddSFCI
还有一些TODO要你来实现了

使用方法：
在192.168.0.150机器上运行：
	sudo python -m pytest ./test_vnfControllerAddSFCI.py -s



# 制作镜像的Dockerfile

这里以testpmd为例制作镜像。（时间久远，可能有错，仅供参考）

```
FROM ubuntu:xenial
WORKDIR /home/t1/bess/deps/dpdk-17.11
COPY .  /home/t1/bess/deps/dpdk-17.11
ENV PATH "$PATH: /home/t1/bess/deps/dpdk-17.11/x86_64-native-linuxapp-gcc/app/"
RUN apt-get update && apt-get install -y \
    numactl \
    libnuma-dev
```

PS1: 需要将Dockerfile放在dpdk文件夹中。

PS2: dockerfile中需要增加 RUN apt-get update && apt-get install libnuma-dev -y，否则会报错libnuma.so.1 not found。

来自 <https://datawine.github.io/2018/07/15/DPDK-Pktgen-Docker%E6%90%AD%E5%BB%BAVNF%E7%8E%AF%E5%A2%83%E5%8F%8A%E9%AA%8C%E8%AF%81/> 

# 使用fastclick简化DPDK开发

https://github.com/tbarbette/fastclick

## fastclick配置

```
./configure --enable-dpdk --enable-multithread --disable-linuxmodule --enable-intel-cpu --enable-user-multithread --verbose --enable-select=poll CFLAGS="-O3" CXXFLAGS="-std=c++11 -O3"  --disable-dynamic-linking --enable-poll --enable-bound-port-transfer --enable-local --enable-flow --disable-task-stats --disable-cpu-load

make
```

## 制作镜像文件

```
FROM ubuntu:latest  
WORKDIR /home/t1/bess/deps
COPY . /home/t1/bess/deps
RUN apt-get update && apt-get install -y \
    numactl  \
    libnuma-dev \
    time \
    iproute2 \
    python \
    libpcap-dev \
    linux-headers-generic \
    pciutils \
    kmod \
```

PS1: ubuntu版本不能太老，否则会报libstdc++的版本错误。

PS2: 把dpdk和fastclick的文件都得打包进来，相比单纯的dpdk，fastclick会多用到几个必须安装的库。

## 最简单的fastclick-dpdk应用:

```
in0 :: FromDPDKDevice(0);
out0 :: ToDPDKDevice(0);
in1 :: FromDPDKDevice(1);
out1 ::ToDPDKDevice(1);
in0 -> Print() -> out1;
in1 -> Print() -> out0;
```

运行命令：

```
fastclick/bin/click --dpdk -l 0-1 -n 1 -m 1024 --no-pci --vdev=net_virtio_user0,path=/tmp/vsock_XXX --vdev=net_virtio_user1,path=/tmp/vsock_XXX -- ./test-dpdk.click
```