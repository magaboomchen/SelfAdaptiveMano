#include <string>

#include "pcapReader.h"

using namespace std;

#ifndef PCAPWRITER_H
#define PCAPWRITER_H


class PcapWriter{
    public:
        PcapWriter(void);
        PcapWriter(string filePath);
        void appendPkt(pcap_pkt pcapPkt);
        void closeWriter(void);
    private:
        string filePath;
        pcap_t *pd;
        pcap_dumper_t *pdumper;
};

#endif