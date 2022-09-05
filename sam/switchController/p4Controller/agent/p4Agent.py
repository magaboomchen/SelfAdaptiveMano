import bfrt_grpc.client as client

PRI_MN_ENTRY = 0
PRI_MN = 1

class P4Agent:

    def __init__(self, _addrwithport):
        self.interface = client.ClientInterface(_addrwithport, 0, 0)
        self.target = client.Target(device_id = 0, pipe_id = 0xffff)
        self.interface.bind_pipeline_config('p4nf_sam')
        self.bfrtinfo = self.interface.bfrt_info_get()
        # perhaps add port managerment here
        self.port_table = self.bfrtinfo.table_get("$PORT")
        self.port_table.entry_add(
            self.target,
            [self.port_table.make_key([client.KeyTuple('$DEV_PORT', 128)])],
            [self.port_table.make_data([
                client.DataTuple('$SPEED', str_val="BF_SPEED_100G"),
                client.DataTuple('$FEC', str_val="BF_FEC_TYP_NONE")
            ])]
        )
        self.port_table.entry_mod(
            self.target,
            [self.port_table.make_key([client.KeyTuple('$DEV_PORT', 128)])],
            [self.port_table.make_data([
                client.DataTuple('$AUTO_NEGOTIATION', 2),
                client.DataTuple('$PORT_ENABLE', bool_val=True)
            ])]
        )
        self._set_loopback_port(136)
        self._set_loopback_port(144)
        self._set_loopback_port(152)
        self._set_loopback_port(160)
        self._set_loopback_port(168)
        self._set_loopback_port(176)
        self._set_loopback_port(184)
        self._set_loopback_port(60)
        self._set_loopback_port(52)
        self.res_spi = 0
        self.res_si = 0
        self.res_src = 0
        self.res_dst = 0
    
    def _set_loopback_port(self, _portnum):
        self.port_table.entry_add(
            self.target,
            [self.port_table.make_key([client.KeyTuple('$DEV_PORT', _portnum)])],
            [self.port_table.make_data([
                client.DataTuple('$SPEED', str_val="BF_SPEED_100G"),
                client.DataTuple('$FEC', str_val="BF_FEC_TYP_NONE")
            ])]
        )
        self.port_table.entry_mod(
            self.target,
            [self.port_table.make_key([client.KeyTuple('$DEV_PORT', _portnum)])],
            [self.port_table.make_data([
                client.DataTuple('$LOOPBACK_MODE', str_val="BF_LPBK_MAC_NEAR"),
                client.DataTuple('$AUTO_NEGOTIATION', 2),
                client.DataTuple('$PORT_ENABLE', bool_val=True)
            ])]
        )

    def addMonitorv4(self, _service_path_index, _service_index):
        monitortable = self.bfrtinfo.table_get('SwitchIngress.FlowMonitorv4')
        monitortable.info.key_field_annotation_add('hdr.ipv4_h.src_addr', 'ipv4')
        monitortable.info.key_field_annotation_add('hdr.ipv4_h.dst_addr', 'ipv4')
        monitortable.entry_add(
            self.target,
            [monitortable.make_key([
                client.KeyTuple('hdr.nsh_h.service_path_index', _service_path_index),
                client.KeyTuple('hdr.nsh_h.service_index', _service_index),
                client.KeyTuple('hdr.ipv4_h.dst_addr', '0.0.0.0', '0.0.0.0'),
                client.KeyTuple('hdr.ipv4_h.src_addr', '0.0.0.0', '0.0.0.0'),
                client.KeyTuple("$MATCH_PRIORITY", PRI_MN)
            ])],
            [monitortable.make_data([], 'SwitchIngress.hit_digest_v4')]
        )

    def addMonitorv6(self, _service_path_index, _service_index):
        monitortable = self.bfrtinfo.table_get('SwitchIngress.FlowMonitorv6')
        monitortable.info.key_field_annotation_add('hdr.ipv6_h.src_addr', 'ipv6')
        monitortable.info.key_field_annotation_add('hdr.ipv6_h.dst_addr', 'ipv6')
        monitortable.entry_add(
            self.target,
            [monitortable.make_key([
                client.KeyTuple('hdr.nsh_h.service_path_index', _service_path_index),
                client.KeyTuple('hdr.nsh_h.service_index', _service_index),
                client.KeyTuple('hdr.ipv6_h.dst_addr', '::', '::'),
                client.KeyTuple('hdr.ipv6_h.src_addr', '::', '::'),
                client.KeyTuple("$MATCH_PRIORITY", PRI_MN)
            ])],
            [monitortable.make_data([], 'SwitchIngress.hit_digest_v6')]
        )

    def removeMonitor(self, _service_path_index, _service_index):
        indextable = self.bfrtinfo.table_get('SwitchIngress.MonitorIndex')
        for i in range(0, 256):
            indextable.entry_del(
                self.target,
                [indextable.make_key([
                    client.KeyTuple('hdr.nsh_h.service_path_index', _service_path_index),
                    client.KeyTuple('hdr.nsh_h.service_index', _service_index),
                    client.KeyTuple('ig_md.index_val', i)
                ])]
            )
        monitortable = self.bfrtinfo.table_get('SwitchIngress.FlowMonitor')
        for i in range(0, 65536):
            monitortable.entry_del(
                self.target,
                [monitortable.make_key([
                    client.KeyTuple('hdr.nsh_h.service_path_index', _service_path_index),
                    client.KeyTuple('hdr.nsh_h.service_index', _service_index),
                    client.KeyTuple('ig_md.hash_val', i)
                ])]
            )

    def addIEGress(self, _service_path_index, _service_index, _outport):
        ingresstable = self.bfrtinfo.table_get('SwitchIngress.CounterIngress')
        egresstable = self.bfrtinfo.table_get('SwitchIngress.CounterEgress')
        ingresstable.entry_add(
            self.target,
            [ingresstable.make_key([
                client.KeyTuple('hdr.nsh_h.service_path_index', _service_path_index),
                client.KeyTuple('hdr.nsh_h.service_index', _service_index)
            ])],
            [ingresstable.make_data([], 'SwitchIngress.hit_ingress')]
        )
        egresstable.entry_add(
            self.target,
            [egresstable.make_key([
                client.KeyTuple('hdr.nsh_h.service_path_index', _service_path_index),
                client.KeyTuple('hdr.nsh_h.service_index', _service_index)
            ])],
            [egresstable.make_data([client.DataTuple('portnum', _outport)], 'SwitchIngress.hit_egress')]
        )
    
    def removeIEGress(self, _service_path_index, _service_index):
        ingresstable = self.bfrtinfo.table_get('SwitchIngress.CounterIngress')
        egresstable = self.bfrtinfo.table_get('SwitchIngress.CounterEgress')
        ingresstable.entry_del(
            self.target,
            [ingresstable.make_key([
                client.KeyTuple('hdr.nsh_h.service_path_index', _service_path_index),
                client.KeyTuple('hdr.nsh_h.service_index', _service_index)
            ])]
        )
        egresstable.entry_del(
            self.target,
            [egresstable.make_key([
                client.KeyTuple('hdr.nsh_h.service_path_index', _service_path_index),
                client.KeyTuple('hdr.nsh_h.service_index', _service_index)
            ])]
        )

    def addRateLimiter(self, _service_path_index, _service_index):
        ratelimiter = self.bfrtinfo.table_get('SwitchIngress.RateLimiter')
        ratelimiter.entry_add(
            self.target,
            [ratelimiter.make_key([
                client.KeyTuple('hdr.nsh_h.service_path_index', _service_path_index),
                client.KeyTuple('hdr.nsh_h.service_index', _service_index)
            ])],
            [ratelimiter.make_data([], 'SwitchIngress.hit_ratelimiter')]
        )
    
    def editRateLimiter(self, _service_path_index, _service_index, _cir, _cbs, _pir, _pbs):
        ratelimiter = self.bfrtinfo.table_get('SwitchIngress.RateLimiter')
        ratelimiter.entry_mod(
            self.target,
            [ratelimiter.make_key([
                client.KeyTuple('hdr.nsh_h.service_path_index', _service_path_index),
                client.KeyTuple('hdr.nsh_h.service_index', _service_index)
            ])],
            [ratelimiter.make_data([
                client.DataTuple('$METER_SPEC_CIR_KBPS', _cir),
                client.DataTuple('$METER_SPEC_PIR_KBPS', _pir),
                client.DataTuple('$METER_SPEC_CBS_KBITS', _cbs),
                client.DataTuple('$METER_SPEC_PBS_KBITS', _pbs)
                ], 'SwitchIngress.hit_ratelimiter'
            )]
        )

    def removeRateLimiter(self, _service_path_index, _service_index):
        ratelimiter = self.bfrtinfo.table_get('SwitchIngress.RateLimiter')
        ratelimiter.entry_del(
            self.target,
            [ratelimiter.make_key([
                client.KeyTuple('hdr.nsh_h.service_path_index', _service_path_index),
                client.KeyTuple('hdr.nsh_h.service_index', _service_index)
            ])]
        )

    def addv4FWentry(self, _service_path_index, _service_index, _src_addr, _dst_addr, _src_mask, _dst_mask, _nxt_hdr, _priority, _is_drop):
        statelessfw = self.bfrtinfo.table_get('SwitchIngress.StatelessFirewallv4')
        statelessfw.info.key_field_annotation_add('hdr.ipv4_h.src_addr', 'ipv4')
        statelessfw.info.key_field_annotation_add('hdr.ipv4_h.dst_addr', 'ipv4')
        actionname = 'SwitchIngress.hit_permit_v4'
        if _is_drop == True:
            actionname = 'SwitchIngress.hit_drop_v4'
        statelessfw.entry_add(
            self.target,
            [statelessfw.make_key([
                client.KeyTuple('hdr.nsh_h.service_path_index', _service_path_index),
                client.KeyTuple('hdr.nsh_h.service_index', _service_index),
                client.KeyTuple("hdr.ipv4_h.src_addr", _src_addr, _src_mask),
                client.KeyTuple("hdr.ipv4_h.dst_addr", _dst_addr, _dst_mask),
                client.KeyTuple("hdr.ipv4_h.next_hdr", _nxt_hdr, 255),
                client.KeyTuple("$MATCH_PRIORITY", _priority)
            ])],
            [statelessfw.make_data([], actionname)]
        )
    
    def removev4FWentry(self, _service_path_index, _service_index, _src_addr, _dst_addr, _src_mask, _dst_mask, _nxt_hdr, _priority, _is_drop):
        statelessfw = self.bfrtinfo.table_get('SwitchIngress.StatelessFirewallv4')
        statelessfw.info.key_field_annotation_add('hdr.ipv4_h.src_addr', 'ipv4')
        statelessfw.info.key_field_annotation_add('hdr.ipv4_h.dst_addr', 'ipv4')
        actionname = 'SwitchIngress.hit_permit_v4'
        if _is_drop == True:
            actionname = 'SwitchIngress.hit_drop_v4'
        statelessfw.entry_del(
            self.target,
            [statelessfw.make_key([
                client.KeyTuple('hdr.nsh_h.service_path_index', _service_path_index),
                client.KeyTuple('hdr.nsh_h.service_index', _service_index),
                client.KeyTuple("hdr.ipv4_h.src_addr", _src_addr, _src_mask),
                client.KeyTuple("hdr.ipv4_h.dst_addr", _dst_addr, _dst_mask),
                client.KeyTuple("hdr.ipv4_h.next_hdr", _nxt_hdr, 255),
                client.KeyTuple("$MATCH_PRIORITY", _priority)
            ])]
        )

    def addv6FWentry(self, _service_path_index, _service_index, _src_addr, _dst_addr, _src_mask, _dst_mask, _nxt_hdr, _priority, _is_drop):
        statelessfw = self.bfrtinfo.table_get('SwitchIngress.StatelessFirewallv6')
        statelessfw.info.key_field_annotation_add('hdr.ipv6_h.src_addr', 'ipv6')
        statelessfw.info.key_field_annotation_add('hdr.ipv6_h.dst_addr', 'ipv6')
        actionname = 'SwitchIngress.hit_permit_v6'
        if _is_drop == True:
            actionname = 'SwitchIngress.hit_drop_v6'
        statelessfw.entry_add(
            self.target,
            [statelessfw.make_key([
                client.KeyTuple('hdr.nsh_h.service_path_index', _service_path_index),
                client.KeyTuple('hdr.nsh_h.service_index', _service_index),
                client.KeyTuple("hdr.ipv6_h.src_addr", _src_addr, _src_mask),
                client.KeyTuple("hdr.ipv6_h.dst_addr", _dst_addr, _dst_mask),
                client.KeyTuple("hdr.ipv6_h.next_hdr", _nxt_hdr, 255),
                client.KeyTuple("$MATCH_PRIORITY", _priority)
            ])],
            [statelessfw.make_data([], actionname)]
        )
    
    def removev6FWentry(self, _service_path_index, _service_index, _src_addr, _dst_addr, _src_mask, _dst_mask, _nxt_hdr, _priority, _is_drop):
        statelessfw = self.bfrtinfo.table_get('SwitchIngress.StatelessFirewallv6')
        statelessfw.info.key_field_annotation_add('hdr.ipv6_h.src_addr', 'ipv6')
        statelessfw.info.key_field_annotation_add('hdr.ipv6_h.dst_addr', 'ipv6')
        actionname = 'SwitchIngress.hit_permit_v6'
        if _is_drop == True:
            actionname = 'SwitchIngress.hit_drop_v6'
        statelessfw.entry_del(
            self.target,
            [statelessfw.make_key([
                client.KeyTuple('hdr.nsh_h.service_path_index', _service_path_index),
                client.KeyTuple('hdr.nsh_h.service_index', _service_index),
                client.KeyTuple("hdr.ipv6_h.src_addr", _src_addr, _src_mask),
                client.KeyTuple("hdr.ipv6_h.dst_addr", _dst_addr, _dst_mask),
                client.KeyTuple("hdr.ipv6_h.next_hdr", _nxt_hdr, 255),
                client.KeyTuple("$MATCH_PRIORITY", _priority)
            ])]
        )

    def queryMonitorv4(self, _service_path_index, _service_index, _src_addr, _dst_addr):
        monitortable = self.bfrtinfo.table_get('SwitchIngress.FlowMonitorv4')
        #monitortable.info.key_field_annotation_add('hdr.ipv4_h.src_addr', 'ipv4')
        #monitortable.info.key_field_annotation_add('hdr.ipv4_h.dst_addr', 'ipv4')
        resp = monitortable.entry_get(
            self.target,
            [monitortable.make_key([
                client.KeyTuple('hdr.nsh_h.service_path_index', _service_path_index),
                client.KeyTuple('hdr.nsh_h.service_index', _service_index),
                client.KeyTuple('hdr.ipv4_h.dst_addr', _dst_addr, ((1 << 32) - 1)),
                client.KeyTuple('hdr.ipv4_h.src_addr', _src_addr, ((1 << 32) - 1)),
                client.KeyTuple("$MATCH_PRIORITY", PRI_MN_ENTRY)
            ])], {"from_hw": True},
            monitortable.make_data([client.DataTuple("$COUNTER_SPEC_BYTES"), client.DataTuple("$COUNTER_SPEC_PKTS")], 'SwitchIngress.hit_monitor_v4', get=True)
        )
        data_dict = next(resp)[0].to_dict()
        pktcnt = data_dict["$COUNTER_SPEC_PKTS"]
        bytecnt = data_dict["$COUNTER_SPEC_BYTES"]
        return pktcnt, bytecnt

    def queryMonitorv6(self, _service_path_index, _service_index, _src_addr, _dst_addr):
        monitortable = self.bfrtinfo.table_get('SwitchIngress.FlowMonitorv6')
        #monitortable.info.key_field_annotation_add('hdr.ipv6_h.src_addr', 'ipv6')
        #monitortable.info.key_field_annotation_add('hdr.ipv6_h.dst_addr', 'ipv6')
        resp = monitortable.entry_get(
            self.target,
            [monitortable.make_key([
                client.KeyTuple('hdr.nsh_h.service_path_index', _service_path_index),
                client.KeyTuple('hdr.nsh_h.service_index', _service_index),
                client.KeyTuple('hdr.ipv6_h.dst_addr', _dst_addr, ((1 << 128) - 1)),
                client.KeyTuple('hdr.ipv6_h.src_addr', _src_addr, ((1 << 128) - 1)),
                client.KeyTuple("$MATCH_PRIORITY", PRI_MN_ENTRY)
            ])], {"from_hw": True},
            monitortable.make_data([client.DataTuple("$COUNTER_SPEC_BYTES"), client.DataTuple("$COUNTER_SPEC_PKTS")], 'SwitchIngress.hit_monitor_v6', get=True)
        )
        data_dict = next(resp)[0].to_dict()
        pktcnt = data_dict["$COUNTER_SPEC_PKTS"]
        bytecnt = data_dict["$COUNTER_SPEC_BYTES"]
        return pktcnt, bytecnt
    
    def queryIOamount(self, _service_path_index, _service_index):
        tableingress = self.bfrtinfo.table_get('SwitchIngress.CounterIngress')
        resp = tableingress.entry_get(
            self.target,
            [tableingress.make_key([
                client.KeyTuple('hdr.nsh_h.service_path_index', _service_path_index),
                client.KeyTuple('hdr.nsh_h.service_index', _service_index)
            ])], {"from_hw": True},
            tableingress.make_data([client.DataTuple("$COUNTER_SPEC_BYTES"), client.DataTuple("$COUNTER_SPEC_PKTS")], 'SwitchIngress.hit_ingress', get=True)
        )
        data_dict = next(resp)[0].to_dict()
        ipkt = data_dict["$COUNTER_SPEC_PKTS"]
        ibyte = data_dict["$COUNTER_SPEC_BYTES"]
        tableegress = self.bfrtinfo.table_get('SwitchIngress.CounterEgress')
        resp = tableegress.entry_get(
            self.target,
            [tableegress.make_key([
                client.KeyTuple('hdr.nsh_h.service_path_index', _service_path_index),
                client.KeyTuple('hdr.nsh_h.service_index', _service_index)
            ])], {"from_hw": True},
            tableegress.make_data([client.DataTuple("$COUNTER_SPEC_BYTES"), client.DataTuple("$COUNTER_SPEC_PKTS")], 'SwitchIngress.hit_egress', get=True)
        )
        data_dict = next(resp)[0].to_dict()
        epkt = data_dict["$COUNTER_SPEC_PKTS"]
        ebyte = data_dict["$COUNTER_SPEC_BYTES"]
        return ipkt, ibyte, epkt, ebyte
    
    def waitForDigenst(self):
        learn_filter = self.bfrtinfo.learn_get("digest")
        # learn_filter.info.data_field_annotation_add("src_addr", "ipv6")
        # learn_filter.info.data_field_annotation_add("dst_addr", "ipv6")
        digest = self.interface.digest_get()
        if digest == None:
            return False
        data_list = learn_filter.make_data_list(digest)
        data_dict = data_list[0].to_dict()
        self.res_spi = (data_dict['service_header'] >> 8)
        self.res_si = (data_dict['service_header'] & 255)
        self.res_src = data_dict['src_addr']
        self.res_dst = data_dict['dst_addr']
        print(self.res_spi)
        print(self.res_si)
        print(self.res_src)
        print(self.res_dst)
        return True
    
    def addMonitorEntry(self):
        if self.res_src >= (1 << 32) or self.res_dst >= (1 << 32):
            self.addMonitorEntryv4()
        else:
            self.addMonitorEntryv6()

    def addMonitorEntryv4(self):
        monitortable = self.bfrtinfo.table_get('SwitchIngress.FlowMonitorv4')
        monitortable.entry_add(
            self.target,
            [monitortable.make_key([
                client.KeyTuple('hdr.nsh_h.service_path_index', self.res_spi),
                client.KeyTuple('hdr.nsh_h.service_index', self.res_si),
                client.KeyTuple('hdr.ipv4_h.dst_addr', self.res_dst, ((1 << 32) - 1)),
                client.KeyTuple('hdr.ipv4_h.src_addr', self.res_src, ((1 << 32) - 1)),
                client.KeyTuple("$MATCH_PRIORITY", PRI_MN_ENTRY)
            ])],
            [monitortable.make_data([], 'SwitchIngress.hit_monitor_v4')]
        )

    def addMonitorEntryv6(self):
        monitortable = self.bfrtinfo.table_get('SwitchIngress.FlowMonitorv6')
        monitortable.entry_add(
            self.target,
            [monitortable.make_key([
                client.KeyTuple('hdr.nsh_h.service_path_index', self.res_spi),
                client.KeyTuple('hdr.nsh_h.service_index', self.res_si),
                client.KeyTuple('hdr.ipv6_h.dst_addr', self.res_dst, ((1 << 128) - 1)),
                client.KeyTuple('hdr.ipv6_h.src_addr', self.res_src, ((1 << 128) - 1)),
                client.KeyTuple("$MATCH_PRIORITY", PRI_MN_ENTRY)
            ])],
            [monitortable.make_data([], 'SwitchIngress.hit_monitor_v6')]
        )

