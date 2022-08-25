#!/bin/bash

# # SIMULATOR ZONE
# for expNum in $(seq 0 0)
# do
#     echo "expNum: " ${expNum}
#     for podNum in 32
#     do
#         echo "podNum: " ${podNum}
#         nPoPNum=$(expr ${podNum} \* ${podNum} / 2)
#         echo "nPoPNum: " ${nPoPNum}
#         mkdir -p ./log/topology/${expNum}/fat-tree/
#         python ./topologyScript.py -e ${expNum} -topo fat-tree -p ${podNum} -nPoPNum ${nPoPNum} -serverNum 20 -nfviNum 5   > ./log/topology/${expNum}/fat-tree/k=${podNum}_nPoPNum=${nPoPNum}.log
#     done
# done

# TURBONET ZONE
for expNum in $(seq 0 0)
do
    echo "expNum: " ${expNum}
    for podNum in 4
    do
        echo "podNum: " ${podNum}
        nPoPNum=2
        echo "nPoPNum: " ${nPoPNum}
        mkdir -p ./log/topology/${expNum}/fat-tree/
        python ./topologyScript.py -e ${expNum} -topo fat-tree-turbonet -p ${podNum} -nPoPNum ${nPoPNum}   > ./log/topology/${expNum}/fat-tree/k=${podNum}_nPoPNum=${nPoPNum}.log
    done
done
