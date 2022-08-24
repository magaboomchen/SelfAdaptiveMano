# start 4 terminals
## Terminal 1
```
cd ~/Projects/SelfAdaptiveMano/sam/test/integrate/turbonetZone/addAndDelSFC
python -m pytest ./test_1.py -s --disable-warnings
```

## Terminal 2 (dispatcher will initial orchestrator automatically)
```
cd ~/Projects/SelfAdaptiveMano/sam/dispatcher
python ./dispatcher.py -parallelMode
```

## Terminal 3
```
cd ~/Projects/SelfAdaptiveMano/sam/mediator
python ./mediator.py
```

## Terminal 4
```
cd ~/Projects/SelfAdaptiveMano/sam/measurement
python ./measurer.py
```

## Terminal 5
```
cd ~/Projects/SelfAdaptiveMano/sam/serverController/vnfController
python ./vnfController.py TURBONET_ZONE
```

## Terminal 6
```
cd ~/Projects/SelfAdaptiveMano/sam/serverController/serverManager
python ./serverManager.py TURBONET_ZONE
```

## Terminal 7
```
cd ~/Projects/SelfAdaptiveMano/sam/serverController/sffController
python ./sffControllerCommandAgent.py  TURBONET_ZONE
```

## Terminal 8
```
cd ~/Projects/SelfAdaptiveMano/sam/switchController/p4Controller
python p4controller_stub.py TURBONET_ZONE
```

## Terminal 9 (for test3)
```
cd ~/Projects/SelfAdaptiveMano/sam/regulator
python ./regulator.py
```

## Server 10001 (194)
```
cd ~/Projects/SelfAdaptiveMano/sam/serverAgent
python ./serverAgent.py 0000:05:00.0 eno1 nfvi 2.2.1.195 10001
```

## Server 10002 (173)
```
cd ~/Projects/SelfAdaptiveMano/sam/serverAgent
python ./serverAgent.py 0000:06:00.0 eno1 nfvi 2.2.1.227 10002
```
