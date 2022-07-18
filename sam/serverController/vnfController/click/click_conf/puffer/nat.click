// The first line is the declaration of IPRewriterPatterns, i.e. "nat :: IPRewriterPatterns(NAT pubIP minport-maxport - -)"
rw :: IPRewriter(pattern NAT 0 1, pass 1, TCP_GUARANTEE 1000, UDP_GUARANTEE 1000);

in0 :: FromDPDKDevice(0);
out0 :: ToDPDKDevice(0, N_QUEUES 1);
in1 :: FromDPDKDevice(1);
out1 ::ToDPDKDevice(1, N_QUEUES 1);

// 0 -> 1
class_left :: Classifier(12/0806 20/0001,  // ARP query
                        12/0806 20/0002,   // ARP respond
                        12/0800);          // IP
// 1 -> 0
class_right :: Classifier(12/0806 20/0001,  // ARP query
                         12/0806 20/0002,   // ARP respond
                         12/0800);          // IP

in0 -> class_left;
in1 -> class_right;

// free for arp
class_left[0] -> out1;
class_left[1] -> out1;
class_right[0] -> out0;
class_right[1] -> out0;

// only allow ip-in-ip
ipip_left :: IPFilter(allow ipip);
ipip_right :: IPFilter(allow ipip);
class_left[2] -> Strip(14) -> CheckIPHeader2() -> ipip_left;
class_right[2] -> Strip(14) -> CheckIPHeader2() -> ipip_right;

ipip_left -> StripIPHeader() -> CheckIPHeader2() -> IPPrint(Before) -> [0]rw;
ipip_right -> StripIPHeader() -> CheckIPHeader2() -> IPPrint(Before) -> [1]rw;

rw[0] -> IPPrint(After) -> Unstrip(34) -> out1;
rw[1] -> IPPrint(After) -> Unstrip(34) -> out0;

ControlSocket(tcp, 8080, VERBOSE true)
