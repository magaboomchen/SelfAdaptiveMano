# SelfAdaptiveMano

SelfAdaptiveMano (SAM) is a NFV Management and Orchestration Platform based on docker API, BESS and P4 Switches.

More information can be obtained in doc folder.

# Environment

Python2.7

Ubuntu 16.04 LTS

# Dependency

## python
```
psutil
pika
netifaces
getmac
pytest
MySQL-python
```

# Installation
## Set SAM python environment
```
Manual:
cd /usr/local/lib/python2.7/dist-packages
sudo vim selfAdaptiveMano.pth
(write) PATH_TO_SELFADAPTIVEMANO

Auto:
python environmentSetter.py
```

## RabbitMQ
```
install erlang 20.3.8.26-1 (please make sure the version number)
rabbitmq3.7.0-1 (please make sure the version number)
```

## Set mysql database
```
add user dbAgent with password 123
add databases Orchestrator, Dashboard, Measurer
```

## Set SAM DPDK environment (Except for Controller server)
export $RTE_SDK to the directory of dpdk in bess, for example:
``` 
export RTE_SDK=/home/t1/Projects/bess/deps/dpdk-17.11/
export RTE_TARGET=x86_64-native-linuxapp-gcc
```

## Set RYU App path
```
RYU_APP_PATH=/usr/local/lib/python2.7/dist-packages/ryu/app
```

# FYI

Please read files in "/doc/SoftwareRequirements/", "/doc/SoftwareDesign/" (Ignore the TODO sections)

Our architecture design is illustrated in Architecture-P4.pptx

Yuxuan Zhang needs to give a design of P4 controller according to our requirements written in Architecture-P4.pptx.

We need to discuss together and then work it out.

# BUG LIST

vnfcontroller
* (not sure) it will get stuck when delete vnfi if vnfi has existed
* can't support multi-core click (maybe the problem of sff? fastclick use RSS to enable multi-core)

sffController
* vnf can't use multi-core, increase queue number in PMDPort(RSS)

integration
* None

# TODO LIST

Readme.md
* add rabbitmq setting

Base
* add routing/addressing scheme name to sfci's attributes

Dashboard
* give requirements
* ask Weilin Zhou to give a design
* user can add new routing scheme, stores it to database, sends it to control layer's module
* select routing/addressing scheme
* validate SFCIID selection

Orchestrator
* UFRR mapping: check vnfi in vnfiSequence, delete duplicate vnfi in same server
* UFRR mapping and E2E-P: measure vnf max latency and update function getLatencyOfVNF in performanceModel.py

Measurer
* add self.sendGetSFCIStateCmd()

Adaptive
* give a design

SFFController
* (optional) add getSFCIStatus

ClassifierController
* None

vnfController
* numa node support: numa cpu core and mem allocation
* independent dpdk apps: set different --file-prefix for differenct vnfi
* test chain deployment in one server

NetworkController
* None

Database Agent
* add database agent to orchestrator, measurer, dashboard

# FEATURE REQUEST LIST
