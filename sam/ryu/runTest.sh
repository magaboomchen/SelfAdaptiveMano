#!/bin/bash

ryuApps=(\
    $RYU_APP_PATH/ofctl_rest.py\
    L2.py\
    northSouthRouting.py\
    westEastRouting.py\
    uffr.py
    )

for var in ${ryuApps[@]};
do
    echo $var
    python $var
done

ryu-manager --observe-links --wsapi-host 127.0.0.1 --wsapi-port 9090 --verbose ${ryuApps[@]}