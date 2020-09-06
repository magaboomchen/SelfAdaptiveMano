# 开发说明
大部分软件已经安装。

开发前请阅读此部分。

我们要开发vnfController，它的功能是根据mediator发出的ADD_SFCI_CMD，在指定的server上安装/配置/删除指定种类的VNF。

每个VNF都是DPDK开发的，需要运行在vnf中进行隔离。

每个VNF有一个端口，和BESS分配的端口连接。

BESS分配的端口是/tmp文件夹下紫色的文件vsock_XXX

PS：
1）虚拟机192.168.0.150和192.168.0.156用于开发/测试vnfController
2）192.168.0.150运行vnfController，这台机器不能跑bess，因为内存只有512MB
3）192.168.0.156运行bess和vnf，这台机器可以跑bess，但是最多只能放置一个VNF，内存4.5GB
4）拓扑参考pptx

# 人工部署VNF
下面是人工实现部署VNF的过程：

1）在虚拟机（192.168.0.156）中启动vnf，并运行L2forwarding DPDK app。

1.1）启动vnf：

    sudo vnf run -ti --rm --privileged  --name=test \
    -v /mnt/huge_1GB:/dev/hugepages \
    -v /tmp/:/tmp/  \
    dpdk-app-testpmd

1.2）在vnf中运行testpmd：

    ./x86_64-native-linuxapp-gcc/app/testpmd -m 1024 --no-pci \
    --vdev=net_virtio_user0,path=/tmp/vsock0_FW1 \
    --vdev=net_virtio_user0,path=/tmp/vsock1_FW1 \
    --file-prefix=virtio --log-level=8 -- \
    --txqflags=0xf00 --disable-hw-vlan --forward-mode=io --port-topology=chained --total-num-mbufs=2048 -a

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