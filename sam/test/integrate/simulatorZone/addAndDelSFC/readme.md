# start 4 terminals
## Terminal 1
```
cd /src/SelfAdaptiveMano/sam/test/integrate/simulatorZone/addAndDelSFC
python -m pytest ./test_1.py -s --disable-warnings
```

## Terminal 2 (dispatcher will initial orchestrator automatically)
```
cd /src/SelfAdaptiveMano/sam/dispatcher
python ./dispatcher.py -parallelMode
```

## Terminal 3
```
cd /src/SelfAdaptiveMano/sam/mediator
python ./mediator.py
```

## Terminal 4
```
cd /src/SelfAdaptiveMano
python ./sam/simulator/simulator.py
```

## Terminal 5 (for test2 and test3)
```
cd /src/SelfAdaptiveMano/sam/measurement
python ./measurer.py
```

## Terminal 6 (for test3)
```
cd /src/SelfAdaptiveMano/sam/regulator
python ./regulator.py
```

## Terminal 7 (check mysql)
```
sudo mysql
use Orchestrator;
select REQUEST_TYPE,SFC_UUID,STATE,RETRY_CNT from Request;
select ZONE_NAME,SFC_UUID,SFCIID_LIST,STATE from SFC;
select ZONE_NAME,SFCIID,SFC_UUID,STATE,ORCHESTRATION_TIME from SFCI;
```


