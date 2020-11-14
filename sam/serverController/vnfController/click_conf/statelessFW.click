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

// init firewall
fw_left :: IPFilter(file "/rule/statelessFW");
fw_right :: IPFilter(file "/rule/statelessFW");

ipip_left -> StripIPHeader() -> CheckIPHeader2() -> fw_left;
ipip_right -> StripIPHeader() -> CheckIPHeader2() -> fw_right;

// restore and send out. (TODO: Here Unstrip(34 = 14 ether header + 20 ip header), but ip header may not be 20.)
fw_left -> Unstrip(34) -> out1;
fw_right -> Unstrip(34) -> out0;