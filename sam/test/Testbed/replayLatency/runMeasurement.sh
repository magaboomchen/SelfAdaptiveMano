#!/bin/bash

mkdir -p ./exp/

declare -a system_arr=(
    # "E2E-P"
    "NotVia-prSFC"
    # "PUFFER"
    )
declare -a failure_type_arr=(
    # "noFaiure"
    # "linkFailure"
    # "switchFailure"
    # "serverHardwareFailure"
    "serverSoftwareFailure"
    )

function start_measurement {
    pcap_file_name="~/DataSets/dcnTrafficIMC10/univ1_pt18_delVLAN.pcap"
    system_arr_len=${#system_arr[@]}
    for ((i=0;i<system_arr_len;i++)); do
        failure_type_arr_len=${#failure_type_arr[@]}
        for ((j=0;j<failure_type_arr_len;j++)); do
            echo "start measurement of " ${system_arr[i]} " on faliure type:" ${failure_type_arr[j]}
            python replayLatency.py -i ${pcap_file_name} \
               -m cc:37:ab:a0:a8:41 -c 1.1.1.2 -d 3.3.3.2 -f 100 -r 0.085 \
               -s ./exp/throughput.${system_arr[i]}.${failure_type_arr[j]}.csv \
               -l ./exp/latency.${system_arr[i]}.${failure_type_arr[j]}.csv
        done
    done
}

function main {
    start_measurement ${FILE_NAME}
}

main $@
