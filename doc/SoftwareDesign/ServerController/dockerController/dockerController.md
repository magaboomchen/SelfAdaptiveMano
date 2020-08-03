# 开发说明
大部分软件已经安装。

开发前请阅读此部分。

我们要开发dockerController，它的功能是根据dockerControllerTester()发出的dockerCMD，在指定的server上安装/配置/删除指定种类的VNF。

每个VNF都是DPDK开发的，需要运行在docker中进行隔离。

每个VNF有一个端口，和BESS分配的端口连接。

BESS分配的端口是/tmp文件夹下紫色的文件vsock_XXX

PS：虚拟机192.168.122.208用于开发dockerController。

# BESS的使用
部署VNF的前提条件是bess配置了VNF的输入和输出端口，这样在启动docker的时候才可以指定docker连接的vdev path：

1） 首先在terminal 1中启动serverAgent注册server，并启动bess：

    cd ~/Project/SelfAdaptiveMano/src/ServerAgent
    python serverAgent.py  0000:00:08.0 ens3

2）然后在terminal 2中启动bessController用于控制bess：

    cd ~/Project/SelfAdaptiveMano/src/ServerController
    python bessController.py

3）接着在terminal 3中给bessController发送指令：

    cd ~/Project/SelfAdaptiveMano/src/ServerController/test
    python bessControllerTester() 192.168.122.208
        在bess中配置PMDPort端口: add
        删除PMDPort端口配置: del
        退出: ctrl-c 

4） 查看运行结果

    cd ~/bess/bessctl
    sudo ./bessctl
    192.168.122.208:10514 $ show pipeline

应该可以看到一张模块图，里面显示了模块之间的连接关系，其中最重要的就是FW1和NAT1的PMDPort，这些port和docker容器连接。

# 人工部署VNF
下面是人工实现部署docker VNF的过程：

1）在虚拟机（192.168.122.208）中启动docker，并运行L2forwarding DPDK app。

1.1）启动docker：

    sudo docker run -ti --rm --privileged  --name=test \
    -v /mnt/huge_1GB:/dev/hugepages \
    -v /tmp/:/tmp/  \
    dpdk-app-testpmd

1.2）在docker中运行testpmd：

    ./x86_64-native-linuxapp-gcc/app/testpmd -m 1024 --no-pci \
    --vdev=net_virtio_user0,path=/tmp/vsock0_FW1 \
    --vdev=net_virtio_user0,path=/tmp/vsock1_FW1 \
    --file-prefix=virtio --log-level=8 -- \
    --txqflags=0xf00 --disable-hw-vlan --forward-mode=io --port-topology=chained --total-num-mbufs=2048 -a

# dockerController部署VNF
我们要用程序替代人工部署VNF，所以要开发dockerController。

基于dockerapi开发： https://docker-py.readthedocs.io/en/stable/

在dockerController.py中需要写代码的地方已经用logging.error("TODO. Text your code here.")标识出来了。

## PS1：
dockerController类中有一个messageAgent，它负责从dockerControllerTester接收指令，并把指令的执行情况反馈给dockerControllerTester。

## PS2：
dockerController部署VNF与人工部署的区别：

在步骤1.2）在docker中运行testpmd命令

    ./x86_64-native-linuxapp-gcc/app/testpmd -m 1024 --no-pci \
    --vdev=net_virtio_user0,path=/tmp/vsock0_FW1 \
    --vdev=net_virtio_user0,path=/tmp/vsock1_FW1 \
    --file-prefix=virtio --log-level=8 -- \
    --txqflags=0xf00 --disable-hw-vlan --forward-mode=io --port-topology=chained --total-num-mbufs=2048 -a

这里的path=/tmp/vsock0_FW1和path=/tmp/vsock1_FW1需要根据dockerCmd来生成。

生成方法：
DockerCmd中给出了每个VNF的UUID。

bessController.py的bessController类中的getVdevOfVNFOutputPMDPort()方法和getVdevOfVNFInputPMDPort()方法可以生成vdev。

这个vdev中的iface=/tmp/vsockX_XXX就是上面命令中path字段的内容。

# dockerControllerTester
已经写好一个测试类dockerControllerTester

使用方法：

    python dockerControllerTester.py 192.168.122.208
        在docker中安装VNF: add
        删除VNF: del
        退出: ctrl-c