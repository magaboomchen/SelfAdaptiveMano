# 测试过程

start mininet, Classifier, SSF1, SSF2, SSF3 虚拟机

在host上运行 ryu-manager

```shell
runTest.sh
```

在mininet虚拟机中运行 test3.py 

```shell
sudo python test3.py
```

通过ssh分别登录4台VM
```
smith@ubuntu-click-server:~/HaoChen/sshShell$ ./sshClassifier.sh
smith@ubuntu-click-server:~/HaoChen/sshShell$ ./sshVNF1.sh
smith@ubuntu-click-server:~/HaoChen/sshShell$ ./sshVNF1Backup0.sh
smith@ubuntu-click-server:~/HaoChen/sshShell$ ./sshVNF1Backup1.sh
t1@BESS-Generator:~$ cd Projects/SelfAdaptiveMano/sam/serverAgent/
```

分别启动serverAgent(如果报错，可以尝试sudo killall bessd)
```
python ./serverAgent.py 0000:00:08.0 ens3 classifier 2.2.0.35
python ./serverAgent.py 0000:00:08.0 ens3 nfvi 2.2.0.68
python ./serverAgent.py 0000:00:08.0 ens3 nfvi 2.2.0.70
python ./serverAgent.py 0000:00:08.0 ens3 nfvi 2.2.0.98
```

<br />

## UFRR 测试

在 testServer 上运行test_UFRR.py

```
sudo python -m pytest ./test_UFRR.py -s --disable-warnings
```


根据提示，在mininet中输入0启动UFRR测试；

输入cli进入命令行模式，常用命令：

```
h1 ping h2
link s1 s2 down
s2 ip link set dev eth2 down 
```

<br />

## NotVia + remapping 测试

在 testServer 上运行test_NotViaReMapping.py

```
sudo python -m pytest ./test_NotViaReMapping.py -s --disable-warnings
```

根据提示，在mininet中输入1启动NotVia+Remapping测试；输入cli进入命令行模式

<br />

## NotVia 测试

在 testServer 上运行test_NotVia.py

```
sudo python -m pytest ./test_NotVia.py -s --disable-warnings
```

根据提示，在mininet中输入2启动NotVia测试；输入cli进入命令行模式


<br />

## PSFC 测试

在 testServer 上运行test_PSFC.py

```
sudo python -m pytest ./test_PSFC.py -s --disable-warnings
```

根据提示，在mininet中输入2启动PSFC测试；输入cli进入命令行模式


<br />

## E2E Protection 测试

在 testServer 上运行test_E2EP.py

```
sudo python -m pytest ./test_E2EP.py -s --disable-warnings
```

根据提示，在mininet中输入2启动E2EP测试；输入cli进入命令行模式
