#!/bin/bash

if [ "$1" == "UFFR" ]
then
    echo "ryu-manager start UFFR"
    ryuApps=(\
        $RYU_APP_PATH/ofctl_rest.py\
        L2.py\
        northSouthRouting.py\
        westEastRouting.py\
        ufrr.py\
        ryuCommandAgentUFRR.py
        )
# elif [ "$1" == "notVia-VLAN" ]
# then
#     echo "ryu-manager start NotVia"
#     ryuApps=(\
#         $RYU_APP_PATH/ofctl_rest.py\
#         L2.py\
#         northSouthRouting.py\
#         westEastRouting.py\
#         notViaVLAN.py\
#         ryuCommandAgentNotViaVLAN.py
#         )
# elif [ "$1" == "notViaMPLS-PSFC" ]
# then
#     echo "ryu-manager start NotVia based on MPLS and PSFC"
#     ryuApps=(\
#         $RYU_APP_PATH/ofctl_rest.py\
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
        $RYU_APP_PATH/ofctl_rest.py\
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
        $RYU_APP_PATH/ofctl_rest.py\
        L2.py\
        northSouthRouting.py\
        westEastRouting.py\
        e2eProtection.py\
        ryuCommandAgentE2EProtection.py
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
