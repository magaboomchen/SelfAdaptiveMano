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

function disableSRIOV {
    local PCIE_DEVICE_NUM=${1}
    echo 0 > /sys/bus/pci/devices/${PCIE_DEVICE_NUM}/sriov_numvfs
}

function printDpdkDevBind {
    local DPDK_DIRECTORY=${1}
    ${DPDK_DIRECTORY}/usertools/dpdk-devbind.py -s
}

function main {
    RTE_SDK="/data/smith/Projects/DPDK/dpdk-21.05"
    updateDriver ${RTE_SDK} "0000:86:00.0" "ixgbe"
    disableSRIOV "0000:86:00.0"
    printDpdkDevBind ${RTE_SDK}
}

main $@
