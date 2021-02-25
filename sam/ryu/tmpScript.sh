#!/bin/bash

rm -rf ./log

# ryuApps=(\
#     $RYU_APP_PATH/ofctl_rest.py\
#     L2.py\
#     westEastRouting.py\
#     northSouthRouting.py
#     )

# ryu-manager --observe-links --wsapi-host 127.0.0.1 --wsapi-port 9090 --verbose ${ryuApps[@]}


ryuApps=(\
    L2.py\
    westEastRouting.py\
    northSouthRouting.py\
    ufrr.py\
    ryuCommandAgentUFRR.py
    )

ryu-manager --observe-links  ${ryuApps[@]}
