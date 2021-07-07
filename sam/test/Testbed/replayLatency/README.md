# Usage example
```
tcprewrite -m 1414 --mtu-trunc --enet-vlan=del --infile=./pcap/univ1_pt20.pcap --outfile=./pcap/univ1_pt20_delVLAN.pcap
```
输入pcap文件需要先去掉VLAN

```
python replayLatency.py -i ~/univ1/univ1_pt20_delVLAN.pcap -m 52:67:f7:65:74:00 -c 10.0.0.0 -d 11.0.0.0 -f 32768 -r 20 -s ~/a.csv -l ~/b.csv
```
参数分别是输入pcap、目标mac地址、源IP、目的IP、流数、重放速率、两个输出文件

## DCN traffic set
20的流量大小约为100Mbps

## 192.168.8.20 PUFFER tasks
总流量大小为2Gbps，一共100条流，每条流的带宽都是20Mbps
```
python replayLatency.py -i ~/DataSets/dcnTrafficIMC10/univ1_pt20_delVLAN.pcap -m cc:37:ab:a0:a8:41 -c 1.1.1.2 -d 3.3.3.2 -f 100 -r 20 -s ~/a.csv -l ~/b.csv
```
