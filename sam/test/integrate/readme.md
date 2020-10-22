# 集成测试

# 保证物理网络运行正常

### 启动ryu
```
smith@ubuntu-click-server:~/HaoChen/Project/SelfAdaptiveMano/sam/ryu$ ./runTestWithoutWeb.sh
```

### 启动mininet
在mininet所在虚拟机
```
vm2@vm2:~/Projects/SelfAdaptiveMano/sam/test/FRR$ sudo python ./test2.py 
```

### 启动serverManager
```
smith@ubuntu-click-server:~/HaoChen/Project/SelfAdaptiveMano/sam/serverController/serverManager$ python ./serverManager.py
```

### 启动serverAgent
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

# 启动各种控制器
## classifierController

```
smith@ubuntu-click-server:~/HaoChen/Project/SelfAdaptiveMano/sam/serverController/classifierController$ python ./classifierControllerCommandAgent.py 
```

## sffController
```
smith@ubuntu-click-server:~/HaoChen/Project/SelfAdaptiveMano/sam/serverController/sffController$ python ./sffControllerCommandAgent.py 
```

## vnfController
```
smith@ubuntu-click-server:~/HaoChen/Project/SelfAdaptiveMano/sam/serverController/vnfController$ python ./vnfController.py
```

# 启动MANO

### mediator

```
smith@ubuntu-click-server:~/HaoChen/Project/SelfAdaptiveMano/sam/mediator$ python ./mediator.py 
```

### measurer
```
smith@ubuntu-click-server:~/HaoChen/Project/SelfAdaptiveMano/sam/measurement$ python ./measurer.py 
```

### orchestrator
```
smith@ubuntu-click-server:~/HaoChen/Project/SelfAdaptiveMano/sam/orchestration$ python ./orchestrator.py 
```




