#!/bin/bash

ryuApps=(\
    L2.py\
    westEastRouting.py\
    northSouthRouting.py\
    uffr.py\
    ryuCommandAgent.py
    )

for var in ${ryuApps[@]};
do
    echo $var
    python $var
done

ryu-manager --observe-links ${ryuApps[@]}