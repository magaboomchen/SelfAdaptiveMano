# Datapath Test Topology
Tester server (8.20) use ens5f1 (Linux kernel)
DUT's host OS (20.6) use PCIE NIC 0000:86:00.0 (DPDK), enable two VF devices.
DUT VM use two PCIE VF NICs, 0000:06:00.0 and 0000:07:00.0

# INSTALLATION
## Fastclick
https://github.com/tbarbette/fastclick
https://github.com/tbarbette/fastclick/wiki/High-speed-I-O
Install DPDK 20.11.5

```
./configure   --enable-multithread --disable-linuxmodule --enable-intel-cpu --enable-user-multithread --verbose CFLAGS="-g -O3" CXXFLAGS="-g -std=gnu++11 -O3" --disable-dynamic-linking --enable-poll --enable-bound-port-transfer --enable-dpdk --enable-batch --with-netmap=no --enable-zerocopy --disable-dpdk-pool --disable-dpdk-packet --enable-ipsec  --enable-tunnel  --enable-local --enable-select=poll --enable-flow --disable-task-stats --disable-cpu-load --disable-rsspp  --enable-ip6 --enable-flow
```

# Test Steps
## Enable two VF devices on DUT host OS, then start DUT VM
```
sudo ./sam/serverController/vnfController/test/datapath/setup/host/setup_nic_82599.sh
```

## Run fastclick on DUT VM
```
sudo ./sam/serverController/vnfController/test/datapath/setup/vm/setup_nic_82599.sh
sudo ./bin/click --dpdk -l 2 -n 1 -m 1024 --  ./conf/sam/monitor.click
```

# Enable promisc on Tester NIC
```
sudo ifconfig ens5f1 promisc
```

# Build fastclick container
```
docker build -t samfastclick:v1 .
```

# VNFController Test Topology
## Disable IGB_UIO on host
```
sudo ./sam/serverController/vnfController/test/datapath/setup/host/deSetup.sh
```

## Enable IGB_UIO on VM
```
sudo ./sam/serverController/vnfController/test/datapath/setup/vm/setup_nic_82599.sh
```