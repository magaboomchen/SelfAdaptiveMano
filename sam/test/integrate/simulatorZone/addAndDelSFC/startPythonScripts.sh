#!/bin/bash

cd ~/Projects/SelfAdaptiveMano/sam/dispatcher
rm -rf log
nohup python ./dispatcher.py -parallelMode &


cd ~/Projects/SelfAdaptiveMano/sam/mediator
rm -rf log
nohup python ./mediator.py &


cd ~/Projects/SelfAdaptiveMano
rm -rf log
# nohup python ./sam/simulator/simulator.py &


cd ~/Projects/SelfAdaptiveMano/sam/measurement
rm -rf log
nohup python ./measurer.py &


cd ~/Projects/SelfAdaptiveMano/sam/regulator
rm -rf log
nohup python ./regulator.py &

