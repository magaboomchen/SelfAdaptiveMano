// init ipsecLookup
rt :: RadixIPsecLookup(


      );

// RadixIPsecLookup Example
//rt :: RadixIPsecLookup(
//      3.3.3.3/32 0 234 \<11FF0183A9471ABE01FFFA04103BB102>  \<11FF0183A9471ABE01FFFA04103BB202>  300 64,
//      0.0.0.0/0 4.4.4.4 1 234 \<11FF0183A9471ABE01FFFA04103BB102>  \<11FF0183A9471ABE01FFFA04103BB202>  300 64
//      );

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
class_left[2]  -> Strip(14) -> CheckIPHeader2() -> ipip_left;
class_right[2] -> Strip(14) -> CheckIPHeader2() -> ipip_right;

// setup clickboard
cb_left :: Clipboard(0/14, 14/2, 18/16);
cb_right :: Clipboard(0/14, 14/2, 18/16);

// Connect VPN
      rt[1] 
      //-> Print(BeforeAddESP, MAXLENGTH 1000)
      -> IPsecESPEncap()
      //-> Print(AfterAddESP, MAXLENGTH 1000)
      -> IPsecAuthHMACSHA1(0)
      //-> Print(AfterAddAH, MAXLENGTH 1000)
      -> IPsecAES(1)
      //-> Print(AfterAES, MAXLENGTH 1000)
      -> IPsecEncap(50)
      -> StoreIPAddress(3.3.3.3, src)
      -> CheckIPHeader2()
      -> IPEncap(4, 0.0.0.0, 0.0.0.0)
      -> EtherEncap(0x0800, 0:0:0:0:0:0, 0:0:0:0:0:0) -> CheckIPHeader2(14) -> [1]cb_left;
      cb_left[1] 
      //-> Print(GetInTunnel_AfterClicBoard, MAXLENGTH 200) 
      -> out1;

      rt[0] 
      -> StripIPHeader()
      -> IPsecAES(0)
      -> IPsecAuthHMACSHA1(1)
      -> IPsecESPUnencap()
      -> CheckIPHeader()
      -> IPEncap(4, 0.0.0.0, 0.0.0.0)
      -> EtherEncap(0x0800, 0:0:0:0:0:0, 0:0:0:0:0:0) -> CheckIPHeader2(14) -> [1]cb_right;
      cb_right[1] 
      //-> Print(GetOutTunnel_AfterClicBoard, MAXLENGTH 200) 
      -> out0;

ipip_left -> Unstrip(14) -> [0]cb_left;
cb_left[0] -> Strip(34) -> CheckIPHeader2() -> rt;
ipip_right -> Unstrip(14) -> [0]cb_right;
cb_right[0] -> Strip(34) -> CheckIPHeader2(0) -> rt;
