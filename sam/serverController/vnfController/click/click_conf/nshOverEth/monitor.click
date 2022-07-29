ControlSocket(tcp, 7777, VERBOSE true)

ipv4_mon_direction0 :: AggregateEthNetworkAddrPair(NETWORK_MORPHIC 0)
ipv4_mon_direction1 :: AggregateEthNetworkAddrPair(NETWORK_MORPHIC 0)
ipv6_mon_direction0 :: AggregateEthNetworkAddrPair(NETWORK_MORPHIC 1)
ipv6_mon_direction1 :: AggregateEthNetworkAddrPair(NETWORK_MORPHIC 1)
rocev1_mon_direction0 :: AggregateEthNetworkAddrPair(NETWORK_MORPHIC 3)
rocev1_mon_direction1 :: AggregateEthNetworkAddrPair(NETWORK_MORPHIC 3)

in0 :: FromDPDKDevice(0, N_QUEUES 1, MODE none, NUMA true);
out0 :: ToDPDKDevice(0, N_QUEUES 1);
in1 :: FromDPDKDevice(1, N_QUEUES 1, MODE none, NUMA true);
out1 ::ToDPDKDevice(1, N_QUEUES 1);

// 0 -> 1
class_direction0 :: Classifier(12/0806 20/0001,  // ARP query
                        12/0806 20/0002,         // ARP respond
                        12/894F                  // NSH
                        );
innerclass_direction0 :: Classifier(
                        3/01,            // IPv4
                        3/02,            // IPv6
                        3/06             // RoceV1
                        );
// 1 -> 0
class_direction1 :: Classifier(12/0806 20/0001,  // ARP query
                         12/0806 20/0002,        // ARP respond
                         12/894F                 // NSH
                         );
innerclass_direction1 :: Classifier(
                        3/01,            // IPv4
                        3/02,            // IPv6
                        3/06             // RoceV1
                        );  


in0 -> class_direction0;
in1 -> class_direction1;

// free for arp
class_direction0[0] -> out1;
class_direction0[1] -> out1;
class_direction1[0] -> out0;
class_direction1[1] -> out0;

// Inner classifier
class_direction0[2] -> Strip(14) -> innerclass_direction0;
class_direction1[2] -> Strip(14) -> innerclass_direction1;


innerclass_direction0[0] -> Strip(24) -> CheckIPHeader2() -> ipv4_mon_direction0;
innerclass_direction1[0] -> Strip(24) -> CheckIPHeader2() -> ipv4_mon_direction1;
// restore and send out. (TODO: Here Unstrip(34 = 14 ether header + 20 ip header), but ip header may not be 20.)
ipv4_mon_direction0 -> Unstrip(38) -> out1;
ipv4_mon_direction1 -> Unstrip(38) -> out0;
//ipv4_mon_direction0 -> Unstrip(38) -> EtherMirror() -> out0;
//ipv4_mon_direction1 -> Unstrip(38) -> EtherMirror() -> out1;


innerclass_direction0[1] -> Strip(24) -> CheckIP6Header() -> ipv6_mon_direction0;
innerclass_direction1[1] -> Strip(24) -> CheckIP6Header() -> ipv6_mon_direction1;

// restore and send out. (TODO: Here Unstrip(34 = 14 ether header + 20 ip header), but ip header may not be 20.)
ipv6_mon_direction0 -> Unstrip(38) -> out1;
ipv6_mon_direction1 -> Unstrip(38) -> out0;
//ipv6_mon_direction0 -> Unstrip(38) -> EtherMirror() -> out0;
//ipv6_mon_direction1 -> Unstrip(38) -> EtherMirror() -> out1;


innerclass_direction0[2] -> Strip(24) -> CheckIP6Header() -> rocev1_mon_direction0;
innerclass_direction1[2] -> Strip(24) -> CheckIP6Header() -> rocev1_mon_direction1;
// restore and send out. (TODO: Here Unstrip(34 = 14 ether header + 20 ip header), but ip header may not be 20.)
//rocev1_mon_direction0 -> Unstrip(38) -> out1;
//rocev1_mon_direction1 -> Unstrip(38) -> out0;
rocev1_mon_direction0 -> Unstrip(38) -> EtherMirror() -> out0;
rocev1_mon_direction1 -> Unstrip(38) -> EtherMirror() -> out1;

DriverManager(
write ipv4_mon_direction0.genRate,
write ipv4_mon_direction1.genRate,
write ipv6_mon_direction0.genRate,
write ipv6_mon_direction1.genRate,
write rocev1_mon_direction0.genRate,
write rocev1_mon_direction1.genRate,
wait 1s,
//read ipv4_mon_direction0.stat,
loop
)