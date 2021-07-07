#include <string>

#include "pcapReader.h"
#include "pcapWriter.h"

using namespace std;

#ifndef PCAPREWRITER_H
#define PCAPREWRITER_H


class PcapRewriter{
    public:
        PcapRewriter(PcapReader pr, PcapWriter pw);
        void setPolicy(string dstipmap, string srcipmap, int flowcnt);
        void rewrite(void);
    private:
        PcapReader pr;
        PcapWriter pw;
        string dstipmap;
        string srcipmap;
        int flowcnt;

        bool isValidPkt(pcap_pkt pcapPkt);
        void rewriteDstIP(pcap_pkt &pcapPkt, string ipstr);
        void rewriteSrcIP(pcap_pkt &pcapPkt, string ipstr);
        void trun(pcap_pkt &pcapPkt);
        void addIPTunnel(pcap_pkt &pcapPkt);
};

#endif