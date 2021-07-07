#include <pcap.h>
#include <gflags/gflags.h>
#include <glog/logging.h>

#include "pcapReader.h"

using namespace std;


PcapReader::PcapReader(void){
    LOG(INFO) << "Initial PcapReader" ;
    packetCount = 0;
}

PcapReader::PcapReader(string filePath){
    LOG(INFO) << "Initial PcapReader" ;
    this->filePath = filePath;
    this->pcap = pcap_open_offline(filePath.c_str(), errbuff);
    packetCount = 0;
}

pcap_pkt PcapReader::getNextPkt(void){
    int rv = pcap_next_ex(pcap, &headerPointer, &dataPointer);
    if(rv >= 0){
        memcpy(&(pcapPkt.header), headerPointer, sizeof(pcapPkt.header));
        memcpy(pcapPkt.data, dataPointer, sizeof(pcapPkt.data));
    }else{
        throw std::invalid_argument("End of pcap file.");
    }

    return pcapPkt;
}