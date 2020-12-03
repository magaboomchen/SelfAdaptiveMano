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

## Set SAM DPDK environment
export $RTE_SDK to the directory of dpdk in bess, for example:
``` 
export RTE_SDK=/home/t1/Projects/bess/deps/dpdk-17.11/
export RTE_TARGET=x86_64-native-linuxapp-gcc
```

## Set mysql database
```
add user dbAgent with password 123
add databases Orchestrator, RequestProcessor, Measurer
```

# FYI

Please read files in "/doc/SoftwareRequirements/", "/doc/SoftwareDesign/" (Ignore the TODO sections)

Our architecture design is illustrated in Architecture-P4.pptx

Yuxuan Zhang needs to give a design of P4 controller according to our requirements written in Architecture-P4.pptx.

We need to discuss together and then work it out.

# BUG LIST

vnfcontroller
* (not sure) it will get stuck when delete vnfi if vnfi has existed

integration
* Null

# TODO LIST

Add zone to all controller
* Simulator as SIMULATOR_ZONE
* Mininet as MININET_ZONE
* Turbonet as TURBONET_ZONE
* "" as DEFAULT_ZONE

Base
* link adds bandwidth, traffic rate
* add routing/addressing scheme name to sfci's attributes
* rename ForwardingPathSet, VNFISequence, SFCIID in class SFCI(object)

Dashboard
* give requirements
* ask Weilin Zhou to give a design
* user can add new routing scheme, stores it to database, sends it to control layer's module
* select routing/addressing scheme
* validate SFCIID selection

Orchestrator
* UFRR mapping: check vnfi in VNFISequence, delete duplicate vnfi in same server
* store reservation of resource for each elements in information base

Measurer
* add self.sendGetSFCIStateCmd()

Adaptive
* give a design

SFFController
* (optional) add getSFCIStatus

ClassifierController
* Null

vnfController
* numa node support: numa cpu core and mem allocation
* independent dpdk apps: set different --file-prefix for differenct vnfi

NetworkController
* Null

Database Agent
* add database agent to orchestrator, measurer, dashboard

# FEATURE REQUEST LIST