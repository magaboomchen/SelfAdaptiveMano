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

// init VPN
vpn_left :: IPsecESPEncap();
vpn_left -> cauth :: IPsecAuthHMACSHA1(0)
        -> encr :: IPsecAES(1);

vpn_right ::  IPsecAES(0);
vpn_right -> vauth :: IPsecAuthHMACSHA1(1)
      -> espuncap :: IPsecESPUnencap();

ipip_left -> StripIPHeader() -> CheckIPHeader2() -> vpn_left;
ipip_right -> StripIPHeader() -> CheckIPHeader2() -> vpn_right;

// restore and send out.
encr -> Unstrip(34) -> out1;
espuncap -> Unstrip(34) -> out0;
