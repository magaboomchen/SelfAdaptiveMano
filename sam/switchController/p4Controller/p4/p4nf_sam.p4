#include <core.p4>
#if __TARGET_TOFINO__ == 2
#include <t2na.p4>
#else
#include <tna.p4>
#endif

// ---------------- headers ----------------

struct digest_t {
    bit<24> service_path_index;
    bit<8> service_index;
    bit<128> dst_addr;
    bit<128> src_addr;
}

header ethernet_hdr {
    bit<48> dst_mac;
    bit<48> src_mac;
    bit<16> ethertype;
}

const bit<16> L16_8 = 0x0800;
const bit<16> L16_8ONE = 0x0801;
const bit<16> ETHERTYPE_IPV4 = 16w0x0800;
const bit<16> ETHERTYPE_NSH = 16w0x894F;
const bit<6> NSH_HEADER_LEN_WORD = 2;
const PortId_t EGRESS_PORT = 128;
const bit<8> ICMP_ECHO_REQUEST = 8;
const bit<8> ICMP_ECHO_REPLY = 0;
const bit<32> NF_ADDR = 0xc0a86404;
const bit<8> MINUS_ONE = 0x01;
const bit<96> L96_ZERO = 0;

#define MAX_NFS 1024
#define MAX_MN_RULES 2048
#define MAX_INDEX_RULES 1024
#define MAX_FW_RULES 2048

header nsh_hdr {
    bit<2> version;
    bit<1> oam;
    bit<1> unsigned_bits_1;
    bit<6> ttl;
    bit<6> header_len;
    bit<4> unsigned_bits_2;
    bit<4> metadata_type;
    bit<8> next_hdr;
    bit<24> service_path_index;
    bit<8> service_index;
}

const bit<8> PROTOCOL_IPV4 = 1;
const bit<8> PROTOCOL_IPV6 = 2;
const bit<8> PROTOCOL_RDMA = 6;

header nsh_context {
    bit<128> context_metadata;
}

header ipv4_hdr {
    bit<4> version;
    bit<4> ihl;
    bit<8> diffserv;
    bit<16> total_len;
    bit<16> identification;
    bit<3> flags;
    bit<13> frag_offset;
    bit<8> ttl;
    bit<8> next_hdr;
    bit<16> hdr_checksum;
    bit<32> src_addr;
    bit<32> dst_addr;
}

header ipv6_hdr {
    bit<4> version;
    bit<8> traffic_class;
    bit<20> flow_label;
    bit<16> payload_len;
    bit<8> next_hdr;
    bit<8> hop_limit;
    bit<128> src_addr;
    bit<128> dst_addr;
}

header icmp_hdr {
    bit<8> icmp_type;
    bit<8> icmp_code;
    bit<16> hdr_checksum;
}

struct ig_header_t {
    ethernet_hdr eth_h;
    nsh_hdr nsh_h;
    ipv4_hdr ipv4_h;
    ipv6_hdr ipv6_h;
    icmp_hdr icmp_h;
    nsh_context nsh_c;
}

struct ig_metadata_t {
    bit<8> color;
    bit<128> src_digest;
    bit<128> dst_digest;
}

// ---------------- basic ----------------

parser TofinoIngressParser(
        packet_in pkt,
        out ingress_intrinsic_metadata_t ig_intr_md) {
    state start {
        pkt.extract(ig_intr_md);
        transition select(ig_intr_md.resubmit_flag) {
            1 : parse_resubmit;
            0 : parse_port_metadata;
        }
    }

    state parse_resubmit {
        transition reject;
    }

    state parse_port_metadata {
        pkt.advance(PORT_METADATA_SIZE);
        transition accept;
    }
}

// ---------------- ingress parde ----------------

parser SwitchIngressParser(
        packet_in pkt,
        out ig_header_t hdr,
        out ig_metadata_t ig_md,
        out ingress_intrinsic_metadata_t ig_intr_md) {

    TofinoIngressParser() tofino_ingress_parser;

    state start {
        tofino_ingress_parser.apply(pkt, ig_intr_md);
        ig_md.color = 0;
        ig_md.src_addr = 0;
        ig_md.dst_addr = 0;
        transition parse_ethernet;
    }

    state parse_ethernet {
        pkt.extract(hdr.eth_h);
        transition select (hdr.eth_h.ethertype) {
            ETHERTYPE_IPV4: parse_icmp;
            ETHERTYPE_NSH: parse_nsh;
            default: reject;
        }
    }

    state parse_icmp {
        pkt.extract(hdr.ipv4_h);
        pkt.extract(hdr.icmp_h);
        transition accept;
    }

    state parse_nsh {
        pkt.extract(hdr.nsh_h);
        pkt.extract(hdr.nsh_c);
        transition select(hdr.nsh_h.next_hdr) {
            PROTOCOL_IPV4: parse_ipv4;
            PROTOCOL_IPV6: parse_ipv6;
            PROTOCOL_RDMA: parse_grh;
            default: reject;
        }
    }

    state parse_ipv4 {
        pkt.extract(hdr.ipv4_h);
        transition accept;
    }

    state parse_ipv6 {
        pkt.extract(hdr.ipv6_h);
        transition accept;
    }

    state parse_grh {
        pkt.extract(hdr.ipv6_h);
        transition accept;
    }
}

control SwitchIngressDeparser(
        packet_out pkt,
        inout ig_header_t hdr,
        in ig_metadata_t ig_md,
        in ingress_intrinsic_metadata_for_deparser_t ig_intr_dprsr_md) {
    Digest<digest_t>() digest;
    apply {
        if (ig_intr_dprsr_md.digest_type == 1) {
            digest.pack({hdr.nsh_h.service_path_index, hdr.nsh_h.service_index, ig_md.dst_addr, ig_md.src_addr});
        }
        pkt.emit(hdr.eth_h);
        pkt.emit(hdr.nsh_h);
        pkt.emit(hdr.nsh_c);
        pkt.emit(hdr.ipv4_h);
        pkt.emit(hdr.ipv6_h);
        pkt.emit(hdr.icmp_h);
    }
}

// ---------------- ingress main ----------------

control SwitchIngress(
        inout ig_header_t hdr,
        inout ig_metadata_t ig_md,
        in ingress_intrinsic_metadata_t ig_intr_md,
        in ingress_intrinsic_metadata_from_parser_t ig_intr_prsr_md,
        inout ingress_intrinsic_metadata_for_deparser_t ig_intr_dprsr_md,
        inout ingress_intrinsic_metadata_for_tm_t ig_intr_tm_md) {

    DirectCounter<bit<32>>(CounterType_t.PACKETS_AND_BYTES) direct_counter_ingress;
    DirectCounter<bit<32>>(CounterType_t.PACKETS_AND_BYTES) direct_counter_egress;
    DirectCounter<bit<32>>(CounterType_t.PACKETS_AND_BYTES) direct_counter_monitor_v4;
    DirectCounter<bit<32>>(CounterType_t.PACKETS_AND_BYTES) direct_counter_monitor_v6;
    DirectCounter<bit<32>>(CounterType_t.PACKETS_AND_BYTES) direct_counter_index;
    DirectMeter(MeterType_t.BYTES) direct_meter;

    action nop() {}

    action hit_ingress() {
        direct_counter_ingress.count();
    }

    table CounterIngress {
        key = {
            hdr.nsh_h.service_path_index: exact;
            hdr.nsh_h.service_index: exact;
        }
        actions = {
            hit_ingress;
            @defaultonly nop;
        }
        const default_action = nop;
        counters = direct_counter_ingress;
        size = MAX_NFS;
    }

    action hit_monitor_v4() {
        direct_counter_monitor_v4.count();
    }

    action hit_monitor_v6() {
        direct_counter_monitor_v6.count();
    }

    action hit_digest_v4() {
        direct_counter_monitor_v4.count();
        ig_intr_dprsr_md.digest_type = 1;
        ig_md.src_addr = L96_ZERO ++ hdr.ipv4_h.src_addr;
        ig_md.dst_addr = L96_ZERO ++ hdr.ipv4_h.dst_addr;
    }

    action hit_digest_v6() {
        direct_counter_monitor_v6.count();
        ig_intr_dprsr_md.digest_type = 1;
        ig_md.src_addr = hdr.ipv6_h.src_addr;
        ig_md.dst_addr = hdr.ipv6_h.dst_addr;
    }

    table FlowMonitorv4 {
        key = {
            hdr.nsh_h.service_path_index: exact;
            hdr.nsh_h.service_index: exact;
            hdr.ipv4_h.src_addr: ternary;
            hdr.ipv4_h.dst_addr: ternary;
        }
        actions = {
            hit_monitor_v4;
            hit_digest_v4;
            @defaultonly nop;
        }
        const default_action = nop;
        counters = direct_counter_monitor_v4;
        size = MAX_MN_RULES;
    }

    table FlowMonitorv6 {
        key = {
            hdr.nsh_h.service_path_index: exact;
            hdr.nsh_h.service_index: exact;
            hdr.ipv6_h.src_addr: ternary;
            hdr.ipv6_h.dst_addr: ternary;
        }
        actions = {
            hit_monitor_v6;
            hit_digest_v6;
            @defaultonly nop;
        }
        const default_action = nop;
        counters = direct_counter_monitor_v6;
        size = MAX_MN_RULES;
    }

    action hit_drop_v4() {
        ig_intr_dprsr_md.drop_ctl = 0x1;
    }

    action hit_permit_v4() { }

    action hit_drop_v6() {
        ig_intr_dprsr_md.drop_ctl = 0x1;
    }

    action hit_permit_v6() { }

    table StatelessFirewallv4 {
        key = {
            hdr.nsh_h.service_path_index: exact;
            hdr.nsh_h.service_index: exact;
            hdr.ipv4_h.src_addr: ternary;
            hdr.ipv4_h.dst_addr: ternary;
            hdr.ipv4_h.next_hdr: ternary;
        }
        actions = {
            hit_drop_v4;
            hit_permit_v4;
            @defaultonly nop;
        }
        const default_action = nop;
        size = MAX_FW_RULES;
    }

    table StatelessFirewallv6 {
        key = {
            hdr.nsh_h.service_path_index: exact;
            hdr.nsh_h.service_index: exact;
            hdr.ipv6_h.src_addr: ternary;
            hdr.ipv6_h.dst_addr: ternary;
            hdr.ipv6_h.next_hdr: ternary;
        }
        actions = {
            hit_drop_v6;
            hit_permit_v6;
            @defaultonly nop;
        }
        const default_action = nop;
        size = MAX_FW_RULES;
    }

    action hit_ratelimiter() {
        ig_md.color = direct_meter.execute();
    }

    table RateLimiter {
        key = {
            hdr.nsh_h.service_path_index: exact;
            hdr.nsh_h.service_index: exact;
        }
        actions = {
            hit_ratelimiter;
            @defaultonly nop;
        }
        const default_action = nop;
        meters = direct_meter;
        size = MAX_NFS;
    }

    action hit_egress(PortId_t portnum) {
        direct_counter_egress.count();
        ig_intr_tm_md.ucast_egress_port = portnum;
    }

    table CounterEgress {
        key = {
            hdr.nsh_h.service_path_index: exact;
            hdr.nsh_h.service_index: exact;
        }
        actions = {
            hit_egress;
            @defaultonly nop;
        }
        const default_action = nop;
        counters = direct_counter_egress;
        size = MAX_NFS;
    }

    apply {
        ig_md.index_val = ig_md.src_tag[31:24] ^ ig_md.src_tag[15:8];
        ig_md.hash_val = ig_md.src_tag[31:16] ^ ig_md.src_tag[15:0];
        ig_intr_tm_md.bypass_egress = 1w1;
        ig_intr_tm_md.ucast_egress_port = EGRESS_PORT;
        if(hdr.nsh_h.isValid()) {
            CounterIngress.apply();
            if(hdr.ipv4_h.isValid()) {
                FlowMonitorv4.apply();
                StatelessFirewallv4.apply();
            }
            else if(hdr.ipv6_h.isValid()) {
                FlowMonitorv6.apply();
                StatelessFirewallv6.apply();
            }
            RateLimiter.apply();
            if(ig_md.color != 0) {
                ig_intr_dprsr_md.drop_ctl = 1;
            }
            else if(ig_intr_dprsr_md.drop_ctl == 0) {
                hdr.nsh_h.service_index = hdr.nsh_h.service_index - MINUS_ONE;
                CounterEgress.apply();
            }
        }
        else if(hdr.icmp_h.isValid() && hdr.icmp_h.icmp_type == ICMP_ECHO_REQUEST && hdr.ipv4_h.isValid() && hdr.ipv4_h.dst_addr == NF_ADDR) {
            bit<32> tmpaddr = hdr.ipv4_h.src_addr;
            hdr.ipv4_h.src_addr = hdr.ipv4_h.dst_addr;
            hdr.ipv4_h.dst_addr = tmpaddr;
            hdr.icmp_h.icmp_type = ICMP_ECHO_REPLY;
            bit<48> tmpmac = hdr.eth_h.src_mac;
            hdr.eth_h.src_mac = hdr.eth_h.dst_mac;
            hdr.eth_h.dst_mac = tmpmac;
            if(hdr.icmp_h.hdr_checksum[15:8] == 0xff || hdr.icmp_h.hdr_checksum[15:8] == 0xfe || hdr.icmp_h.hdr_checksum[15:8] == 0xfd ||
                hdr.icmp_h.hdr_checksum[15:8] == 0xfc || hdr.icmp_h.hdr_checksum[15:8] == 0xfb || hdr.icmp_h.hdr_checksum[15:8] == 0xfa ||
                hdr.icmp_h.hdr_checksum[15:8] == 0xf9 || hdr.icmp_h.hdr_checksum[15:8] == 0xf8) {
                hdr.icmp_h.hdr_checksum = L16_8ONE + hdr.icmp_h.hdr_checksum;
            }
            else {
                hdr.icmp_h.hdr_checksum = L16_8 + hdr.icmp_h.hdr_checksum;
            }
        }
        else {
            ig_intr_dprsr_md.drop_ctl = 0x1;
        }
    }
}

// ---------------- other ---------------

struct empty_header_t {}

struct empty_metadata_t {}

parser EmptyEgressParser(
        packet_in pkt,
        out empty_header_t hdr,
        out empty_metadata_t eg_md,
        out egress_intrinsic_metadata_t eg_intr_md) {
    state start {
        transition accept;
    }
}

control EmptyEgressDeparser(
        packet_out pkt,
        inout empty_header_t hdr,
        in empty_metadata_t eg_md,
        in egress_intrinsic_metadata_for_deparser_t ig_intr_dprs_md) {
    apply {}
}

control EmptyEgress(
        inout empty_header_t hdr,
        inout empty_metadata_t eg_md,
        in egress_intrinsic_metadata_t eg_intr_md,
        in egress_intrinsic_metadata_from_parser_t eg_intr_md_from_prsr,
        inout egress_intrinsic_metadata_for_deparser_t ig_intr_dprs_md,
        inout egress_intrinsic_metadata_for_output_port_t eg_intr_oport_md) {
    apply {}
}

Pipeline(SwitchIngressParser(),
         SwitchIngress(),
         SwitchIngressDeparser(),
         EmptyEgressParser(),
         EmptyEgress(),
         EmptyEgressDeparser()) pipe;

Switch(pipe) main;
