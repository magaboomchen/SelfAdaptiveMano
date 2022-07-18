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

function enableSRIOV {
    local PCIE_DEVICE_NUM=${1}
    echo "PCIE_DEVICE_NUM:" ${PCIE_DEVICE_NUM}
    local VF_NUM=${2}
    echo "VF_NUM:" ${VF_NUM}
    echo ${VF_NUM} > /sys/bus/pci/devices/${PCIE_DEVICE_NUM}/sriov_numvfs
}

function assignMACAddressToVirtualFunction {
    echo "assignMACAddressToVirtualFunction"
    local INTF_NAME=${1}
    echo "vf mac address"
    sudo ip link set ${INTF_NAME} vf 0 mac 52:67:f7:65:01:00
    sudo ip link set ${INTF_NAME} vf 1 mac 52:67:f7:65:01:01
    sudo ip link set ${INTF_NAME} vf 2 mac 52:67:f7:65:01:02
    sudo ip link set ${INTF_NAME} vf 3 mac 52:67:f7:65:01:03
    # sudo ip link set ${INTF_NAME} vf 4 mac 52:67:f7:65:01:04
    # sudo ip link set ${INTF_NAME} vf 5 mac 52:67:f7:65:01:05
    # sudo ip link set ${INTF_NAME} vf 6 mac 52:67:f7:65:01:06
    # sudo ip link set ${INTF_NAME} vf 7 mac 52:67:f7:65:01:07
    echo "up"
    sudo ip link set ${INTF_NAME} up
}

function bindVirtualFunction {
    echo "bindVirtualFunction"
    PF_PCIE_DEVICE_NUM=${1}
    SLOT_NUM=${2}
    DRIVER_NAME=${3}
    for pcie_suffix in 0 1 2 3 4 5 6 7
    do
        VF_PCIE_DEVICE_NUM=${PF_PCIE_DEVICE_NUM:0:8}${SLOT_NUM}"."${pcie_suffix}
        local DPDK_DIRECTORY=${4}
        echo "binding VF_PCIE_DEVICE_NUM:" ${VF_PCIE_DEVICE_NUM}
        ${DPDK_DIRECTORY}/usertools/dpdk-devbind.py -b ${DRIVER_NAME} ${VF_PCIE_DEVICE_NUM}
    done
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
    RTE_SDK="/data/smith/Projects/DPDK/dpdk-21.05"
    # insertDriver ${RTE_SDK}
    updateDriver ${RTE_SDK} "0000:86:00.0" "ixgbe"
    enableSRIOV "0000:86:00.0" 4
    assignMACAddressToVirtualFunction "ens5f0"
    printDpdkDevBind ${RTE_SDK}
}

main $@
