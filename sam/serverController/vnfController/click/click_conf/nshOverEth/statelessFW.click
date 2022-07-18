define(
	$IPV4FW_RULE_PATH  /home/smith/Projects/fastclick/conf/sam/statelessFWRules,
    $IPV6FW_RULE_PATH  /home/smith/Projects/fastclick/conf/sam/statelessFWIPv6Rules,
    $ROCEV1FW_RULE_PATH  /home/smith/Projects/fastclick/conf/sam/statelessFWRoceV1Rules
);

in0 :: FromDPDKDevice(0, N_QUEUES 1, MODE none);
out0 :: ToDPDKDevice(0, N_QUEUES 1);
in1 :: FromDPDKDevice(1, N_QUEUES 1, MODE none);
out1 ::ToDPDKDevice(1, N_QUEUES 1);

// 0 -> 1
class_direction0 :: Classifier(12/0806 20/0001,  // ARP query
                        12/0806 20/0002,    // ARP respond
                        12/894F             // NSH
                        );
innerclass_direction0 :: Classifier(
                        3/01,            // IPv4
                        3/02,            // IPv6
                        3/06             // RoceV1
                        );       
// 1 -> 0
class_direction1 :: Classifier(12/0806 20/0001,  // ARP query
                        12/0806 20/0002,    // ARP respond
                        12/894F            // NSH
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

// Inner classifier (IPv4 branch):
class_direction0[2] -> Strip(14) -> innerclass_direction0;
class_direction1[2] -> Strip(14) -> innerclass_direction1;


// init ipv4 filter
ipv4fw_direction0 :: IPFilter(file $IPV4FW_RULE_PATH);
ipv4fw_direction1 :: IPFilter(file $IPV4FW_RULE_PATH);

innerclass_direction0[0] -> Strip(24) -> CheckIPHeader2() -> ipv4fw_direction0;
innerclass_direction1[0] -> Strip(24) -> CheckIPHeader2() -> ipv4fw_direction1;

// restore and send out. (TODO: Here Unstrip(34 = 14 ether header + 20 ip header), but ip header may not be 20.)
ipv4fw_direction0 -> Unstrip(38) -> out1;
ipv4fw_direction1 -> Unstrip(38) -> out0;
//ipv4fw_direction0 -> Unstrip(38) -> EtherMirror() -> out0;
//ipv4fw_direction1 -> Unstrip(38) -> EtherMirror() -> out1;


// init ipv6 filter
ipv6fw_direction0 :: LookupIP6Route(file $IPV6FW_RULE_PATH);
ipv6fw_direction1 :: LookupIP6Route(file $IPV6FW_RULE_PATH);

// Inner classifier (IPv6/SRv6/RoceV1 branch):
innerclass_direction0[1] -> Strip(24) -> GetIP6Address(24) -> ipv6fw_direction0;
innerclass_direction1[1] -> Strip(24) -> GetIP6Address(24) -> ipv6fw_direction1;

ipv6fw_direction0[0] -> Discard;
ipv6fw_direction1[0] -> Discard;

ipv6fw_direction0[1] -> Unstrip(38) -> out1;
ipv6fw_direction1[1] -> Unstrip(38) -> out0;
//ipv6fw_direction0[1] -> Unstrip(38) -> EtherMirror() -> out0;
//ipv6fw_direction1[1] -> Unstrip(38) -> EtherMirror() -> out1;


// init rocev1 filter
rocev1fw_direction0 :: LookupIP6Route(file $ROCEV1FW_RULE_PATH);
rocev1fw_direction1 :: LookupIP6Route(file $ROCEV1FW_RULE_PATH);

innerclass_direction0[2] -> Strip(24) -> GetIP6Address(24) -> rocev1fw_direction0;
innerclass_direction1[2] -> Strip(24) -> GetIP6Address(24) -> rocev1fw_direction1;

rocev1fw_direction0[0] -> Discard;
rocev1fw_direction1[0] -> Discard;

rocev1fw_direction0[1] -> Unstrip(38) -> out1;
rocev1fw_direction1[1] -> Unstrip(38) -> out0;
//rocev1fw_direction0[1] -> Unstrip(38) -> EtherMirror() -> out0;
//rocev1fw_direction1[1] -> Unstrip(38) -> EtherMirror() -> out1;
