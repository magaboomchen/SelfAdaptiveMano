#!/bin/bash

rm -rf ./log

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
elif [ "$1" == "notViaNAT-PSFC" ]
then
    echo "ryu-manager start NotVia based on NAT and pSFC"
    ryuApps=(\
        L2.py\
        westEastRouting.py\
        northSouthRouting.py\
        notViaNATAndPSFC.py\
        ryuCommandAgentNotViaNATAndPSFC.py
        )
elif [ "$1" == "e2ep" ]
then
    echo "ryu-manager start E2E Protection"
    ryuApps=(\
        L2.py\
        westEastRouting.py\
        northSouthRouting.py\
        e2eProtection.py\
        ryuCommandAgentE2EProtection.py
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
