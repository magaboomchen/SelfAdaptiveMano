#!/bin/bash

set -euo pipefail

function error_log {
    echo "$1" 1>&2
}

function insertDriver {
    echo "insertDriver"
    local DPDK_DIRECTORY=${1}   # please set $DPDK_DIRECTORY to your dpdk directory
    echo "DPDK_DIRECTORY:" ${DPDK_DIRECTORY}
    sudo chmod a+x /dev/vfio
    sudo chmod 0666 /dev/vfio/*
    modprobe uio
    modprobe vfio
    modprobe vfio-pci
    modprobe msr
    insmod  ${DPDK_DIRECTORY}/kernel/linux/igb_uio/igb_uio.ko || error_log "$LINENO: failed"
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

function allocateHugePages {
    echo "allocateHugePages"
    local NUMA_NODE_NUM=${1}
    local HUGEPAGE_NUM=${2}
    echo ${HUGEPAGE_NUM} > /sys/devices/system/node/node${NUMA_NODE_NUM}/hugepages/hugepages-1048576kB/nr_hugepages
}

function main {
    RTE_SDK="/home/smith/Projects/DPDK/dpdk-stable-20.11.5"
    insertDriver ${RTE_SDK}
    for PCIE_NUM in "0000:06:00.0" "0000:07:00.0"
    do
        updateDriver ${RTE_SDK} ${PCIE_NUM} "igb_uio"
        printDpdkDevBind ${RTE_SDK}
    done
}

main $@
