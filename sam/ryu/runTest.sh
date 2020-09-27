#!/bin/bash

if [ "$1" == "ryu-manager start UFFR" ]
then
    echo "UFFR"
    ryuApps=(\
        $RYU_APP_PATH/ofctl_rest.py\
        L2.py\
        northSouthRouting.py\
        westEastRouting.py\
        ufrr.py\
        ryuCommandAgentUFRR.py
        )
elif [ "$1" == "notVia" ]
then
    echo "ryu-manager start NotVia"
    ryuApps=(\
        $RYU_APP_PATH/ofctl_rest.py\
        L2.py\
        northSouthRouting.py\
        westEastRouting.py\
        notVia.py\
        ryuCommandAgentNotVia.py
        )
else
    echo "ryu-manager start default app: UFFR"
    ryuApps=(\
        $RYU_APP_PATH/ofctl_rest.py\
        L2.py\
        northSouthRouting.py\
        westEastRouting.py\
        ufrr.py\
        ryuCommandAgentUFRR.py
        )
fi

for var in ${ryuApps[@]};
do
    echo $var
    python $var
done

ryu-manager --observe-links --wsapi-host 127.0.0.1 --wsapi-port 9090 --verbose ${ryuApps[@]}
