#!/bin/bash

if [ "$1" == "UFFR" ]
then
    echo "ryu-manager start UFFR"
    ryuApps=(\
        L2.py\
        westEastRouting.py\
        northSouthRouting.py\
        ufrr.py\
        ryuCommandAgentUFRR.py
        )
elif [ "$1" == "notVia" ]
then
    echo "ryu-manager start NotVia"
    ryuApps=(\
        L2.py\
        westEastRouting.py\
        northSouthRouting.py\
        notVia.py\
        ryuCommandAgentNotVia.py
        )
else
    echo "ryu-manager start default app: UFFR"
    ryuApps=(\
        L2.py\
        westEastRouting.py\
        northSouthRouting.py\
        ufrr.py\
        ryuCommandAgentUFRR.py
        )
fi

for var in ${ryuApps[@]};
do
    echo $var
    python $var
done

ryu-manager --observe-links ${ryuApps[@]}