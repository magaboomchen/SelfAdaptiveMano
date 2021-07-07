#include <string>
#include <iostream>

#include <pcap.h>
#include <gflags/gflags.h>
#include <glog/logging.h>

#include "pcapReader.h"
#include "pcapWriter.h"
#include "pcapRewriter.h"

using namespace std;

/*
DECLARE_string(f);
DECLARE_string(w);
DECLARE_string(dstipmap);
DECLARE_string(osrcip);
DECLARE_string(odstip);
DECLARE_int32(trunMTU);

int main(int argc, char *argv[]){
    google::ParseCommandLineFlags(&argc, &argv, true);

    FLAGS_alsologtostderr = 1;
    FLAGS_log_dir = "./log";
    FLAGS_colorlogtostderr = true;
    google::InitGoogleLogging(argv[0]);

    PcapReader pr(FLAGS_f);    // example FLAGS_f = "./pcap/univ1_pt20.pcap"
    PcapWriter pw(FLAGS_w);    // example FLAGS_w = "./pcap/22.pcap"
    PcapRewriter prw(pr, pw);

    prw.setPolicy(FLAGS_dstipmap, FLAGS_osrcip, FLAGS_odstip, FLAGS_trunMTU);
    prw.rewrite();

    pw.closeWriter();
}
*/

DECLARE_string(f);
DECLARE_string(w);
DECLARE_string(dstipmap);
DECLARE_string(srcipmap);
DECLARE_int32(flowcnt);

int main(int argc, char *argv[]){
    google::ParseCommandLineFlags(&argc, &argv, true);

    FLAGS_alsologtostderr = 1;
    FLAGS_log_dir = "./log";
    FLAGS_colorlogtostderr = true;
    google::InitGoogleLogging(argv[0]);

    PcapReader pr(FLAGS_f);    // example FLAGS_f = "./pcap/univ1_pt20.pcap"
    PcapWriter pw(FLAGS_w);    // example FLAGS_w = "./pcap/22.pcap"
    PcapRewriter prw(pr, pw);

    prw.setPolicy(FLAGS_dstipmap, FLAGS_srcipmap, FLAGS_flowcnt);
    prw.rewrite();

    pw.closeWriter();
}
