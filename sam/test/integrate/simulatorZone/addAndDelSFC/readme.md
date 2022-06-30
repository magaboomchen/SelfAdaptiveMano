# start 4 terminals
## Terminal 1
'''
cd ~/Projects/SelfAdaptiveMano/sam/test/integrate/simulatorZone/addAndDelSFC
python -m pytest ./test_1.py -s --disable-warnings
'''

## Terminal 2 (dispatcher will initial orchestrator automatically)
'''
cd ~/Projects/SelfAdaptiveMano/sam/dispatcher
python ./dispatcher.py -parallelMode
'''

## Terminal 3
'''
cd ~/Projects/SelfAdaptiveMano/sam/mediator
python ./mediator.py
'''

## Terminal 4
'''
cd ~/Projects/SelfAdaptiveMano
python ./sam/simulator/simulator.py
'''
