#!/bin/bash


for expNum in $(seq 0 0)
do
    echo "expNum: " ${expNum}
    for podNum in 32
    do
        echo "podNum: " ${podNum}
        nPoPNum=$(expr ${podNum} \* ${podNum} / 2)
        echo "nPoPNum: " ${nPoPNum}
        mkdir -p ./log/topology/${expNum}/fat-tree/
        python ./topologyScript.py -e ${expNum} -topo fat-tree -p ${podNum} -nPoPNum ${nPoPNum}   > ./log/topology/${expNum}/fat-tree/k=${podNum}_nPoPNum=${nPoPNum}.log
    done
done
