# 测试过程

启动 mininet, Classifier, SSF1, SSF2, SSF3 虚拟机

在host上运行 ryu-manager

```shell
runTest.sh
```

在mininet虚拟机中运行 test2.py 

```shell
sudo python test2.py
```

<br />

## UFRR 测试

在 testServer 上运行test_UFRR.py

```
sudo python -m pytest ./test_UFRR.py -s
```


根据提示，在mininet中输入0启动UFRR测试；输入cli进入命令行模式

<br />

## NotVia 测试

在 testServer 上运行test_NotViaReMapping.py

```
sudo python -m pytest ./test_NotViaReMapping.py -s
```

根据提示，在mininet中输入1启动NotVia+Remapping测试；输入cli进入命令行模式
