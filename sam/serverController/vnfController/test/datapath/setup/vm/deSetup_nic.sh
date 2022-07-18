#!/bin/bash

set -euo pipefail

function error_log {
    echo "$1" 1>&2
}

function updateDriver {
    local DPDK_DIRECTORY=${1}   # please set $DPDK_DIRECTORY to your dpdk directory
    echo "DPDK_DIRECTORY:" ${DPDK_DIRECTORY}
    local PCIE_DEVICE_NUM=${2}
    echo "PCIE_DEVICE_NUM:" ${PCIE_DEVICE_NUM}
    local DRIVER_NAME=${3}
    ${DPDK_DIRECTORY}/usertools/dpdk-devbind.py -b ${DRIVER_NAME} ${PCIE_DEVICE_NUM}
}

function printDpdkDevBind {
    local DPDK_DIRECTORY=${1}
    ${DPDK_DIRECTORY}/usertools/dpdk-devbind.py -s
}

function main {
    RTE_SDK="/home/smith/Projects/DPDK/dpdk-stable-20.11.5"
    for PCIE_NUM in "0000:06:00.0" "0000:07:00.0"
    do
        updateDriver ${RTE_SDK} ${PCIE_NUM} "ixgbevf"
        printDpdkDevBind ${RTE_SDK}
    done
}

main $@
