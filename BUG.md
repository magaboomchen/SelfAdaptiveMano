# BUG LIST

vnfcontroller
* (not sure) it will get stuck when delete vnfi if vnfi has existed
* can't support multi-core click (maybe the problem of sff? fastclick use RSS to enable multi-core)

sffController
* vnf can't use multi-core, increase queue number in PMDPort(RSS)
* PUFFER based chain: sfciID can't larger than 255 because update() module rewrite 1 byte from vnfID.
To tackle this bug, please refactor Update() module in bess and refactor sffController.
In details, add "value_maks" arg to Update() to only update vnfID in SFF. 

integration
* None

ryu
* _del_flow() needs add out_port and out_group to make sure the correctness. Refactor all api reference by other module.
