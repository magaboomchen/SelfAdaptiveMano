#include <string>

#include <pcap.h>
#include <gflags/gflags.h>
#include <glog/logging.h>

#include "pcapWriter.h"
#include "pcapReader.h"

using namespace std;


PcapWriter::PcapWriter(void){
    LOG(INFO) << "Initial PcapWriter" ;
    pd = NULL;
    pdumper = NULL;
}

PcapWriter::PcapWriter(string filePath){
    LOG(INFO) << "Initial PcapWriter" ;
    this->filePath = filePath;
    pd = pcap_open_dead(DLT_EN10MB, MAX_PACKET_LENGTH);
    pdumper = pcap_dump_open(pd, filePath.c_str());
}

void PcapWriter::appendPkt(pcap_pkt pcapPkt){
    pcap_dump((u_char*)pdumper, &pcapPkt.header, (const u_char*)pcapPkt.data);
}

void PcapWriter::closeWriter(void){
    LOG(INFO) << "Closing PcapWriter " ;
    if(pd != NULL){
        pcap_close(pd);
        pd = NULL;
    }
    if(pdumper != NULL){
        pcap_dump_close(pdumper);
        pdumper = NULL;
    }
}