#include <string>
#include <iostream>

#include <pcap.h>

#include "global.h"

using namespace std;

#ifndef PCAPREADER_H
#define PCAPREADER_H


struct pcap_pkt{
    struct pcap_pkthdr header;
    u_char data[MAX_PACKET_LENGTH];
};


class PcapReader{
    public:
        PcapReader(void);
        PcapReader(string filePath);
        pcap_pkt getNextPkt(void);
    private:
        string filePath;
        pcap_t * pcap;
        char errbuff[PCAP_ERRBUF_SIZE];
        struct pcap_pkthdr *headerPointer;
        const u_char *dataPointer;
        pcap_pkt pcapPkt;
        u_int packetCount;
};

#endif