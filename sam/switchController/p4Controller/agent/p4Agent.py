import bfrt_grpc.client as client

class P4Agent:

    def __init__(self, _addrwithport):
        self.interface = client.ClientInterface(_addrwithport, 0, 0)
        self.target = client.Target(device_id = 0, pipe_id = 0xffff)
        self.interface.bind_pipeline_config('p4nf_sam')
        self.bfrtinfo = self.interface.bfrt_info_get()
    
    def addMonitor(self, _service_path_index, _service_index):
        indextable = self.bfrtinfo.table_get('SwitchIngress.MonitorIndex')
        for i in range(0, 256):
            indextable.entry_add(
                self.target,
                [indextable.make_key([
                    client.KeyTuple('hdr.nsh_h.service_path_index', _service_path_index),
                    client.KeyTuple('hdr.nsh_h.service_index', _service_index),
                    client.KeyTuple('ig_md.index_val', i)
                ])],
                [indextable.make_data([], 'SwitchIngress.hit_index')]
            )
        monitortable = self.bfrtinfo.table_get('SwitchIngress.FlowMonitor')
        for i in range(0, 65536):
            monitortable.entry_add(
                self.target,
                [monitortable.make_key([
                    client.KeyTuple('hdr.nsh_h.service_path_index', _service_path_index),
                    client.KeyTuple('hdr.nsh_h.service_index', _service_index),
                    client.KeyTuple('ig_md.hash_val', i)
                ])],
                [monitortable.make_data([], 'SwitchIngress.hit_monitor')]
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

    def addIEGress(self, _service_path_index, _service_index, _outport = 64):
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
                client.KeyTuple("hdr.ipv4_h.nxt_hdr", _nxt_hdr, 255),
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
                client.KeyTuple("hdr.ipv4_h.nxt_hdr", _nxt_hdr, 255),
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
                client.KeyTuple("hdr.ipv6_h.nxt_hdr", _nxt_hdr, 255),
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
                client.KeyTuple("hdr.ipv6_h.nxt_hdr", _nxt_hdr, 255),
                client.KeyTuple("$MATCH_PRIORITY", _priority)
            ])]
        )

    def queryIndex(self, _service_path_index, _service_index, _index_val):
        # currently not supported
        pass

    def queryMonitor(self, _service_path_index, _service_index, _hash_val):
        # currently not supported
        pass
    
    def queryIOamount(self, _service_path_index, _service_index):
        tableingress = self.bfrtinfo.table_get('SwitchIngress.CounterIngress')
        tableegress = self.bfrtinfo.table_get('SwitchIngress.CounterEgress')
        return ipkt, ibyte, epkt, ebyte
