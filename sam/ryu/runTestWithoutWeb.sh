#!/bin/bash

if [ "$1" == "UFFR" ]
then
    echo "ryu-manager start UFFR"
    ryuApps=(\
        L2.py\
        northSouthRouting.py\
        westEastRouting.py\
        ufrr.py\
        ryuCommandAgentUFRR.py
        )
# elif [ "$1" == "notViaVLAN" ]
# then
#     echo "ryu-manager start NotVia based on VLAN"
#     ryuApps=(\
#         L2.py\
#         northSouthRouting.py\
#         westEastRouting.py\
#         notViaVLAN.py\
#         ryuCommandAgentNotViaVLAN.py
#         )
# elif [ "$1" == "notViaMPLS-PSFC" ]
# then
#     echo "ryu-manager start NotVia based on MPLS and pSFC"
#     ryuApps=(\
#         L2.py\
#         northSouthRouting.py\
#         westEastRouting.py\
#         notViaMPLSAndPSFC.py\
#         ryuCommandAgentNotViaMPLSAndPSFC.py
#         )
elif [ "$1" == "notViaNAT-PSFC" ]
then
    echo "ryu-manager start NotVia based on NAT and pSFC"
    ryuApps=(\
        L2.py\
        northSouthRouting.py\
        westEastRouting.py\
        notViaNATAndPSFC.py\
        ryuCommandAgentNotViaNATAndPSFC.py
        )
elif [ "$1" == "e2ep" ]
then
    echo "ryu-manager start E2E Protection"
    ryuApps=(\
        L2.py\
        northSouthRouting.py\
        westEastRouting.py\
        e2eProtection.py\
        ryuCommandAgentE2EProtection.py
        )
else
    echo "ryu-manager start default app: UFFR"
    ryuApps=(\
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

ryu-manager --observe-links ${ryuApps[@]}
