// The first line is the declaration of IPLoadBalancer, i.e. "lb :: IPLoadBalancer"
lb_reverse :: IPLoadBalancerReverse(lb);

in0 :: FromDPDKDevice(0);
out0 :: ToDPDKDevice(0);
in1 :: FromDPDKDevice(1);
out1 ::ToDPDKDevice(1);

// 0 -> 1
class_left :: Classifier(12/0806 20/0001,  // ARP query
                        12/0806 20/0002,   // ARP respond
                        12/0800);          // IP
// 1 -> 0
class_right :: Classifier(12/0806 20/0001,  // ARP query
                         12/0806 20/0002,   // ARP respond
                         12/0800);          // IP


in0 -> Print() -> class_left;
in1 -> Print() -> class_right;

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

ipip_left -> IPPrint(Left-Outer) -> StripIPHeader() -> CheckIPHeader2() -> IPPrint(Left-Inner) -> lb;
ipip_right -> IPPrint(Right-Outer) -> StripIPHeader() -> CheckIPHeader2() -> IPPrint(Right-Inner) -> lb_reverse;

// restore and send out. (TODO: Here Unstrip(34 = 14 ether header + 20 ip header), but ip header may not be 20.)
lb -> IPPrint(After-LB) -> Unstrip(34) -> out1;
lb_reverse -> IPPrint(After-LB-REVERSE) -> Unstrip(34) -> out0;