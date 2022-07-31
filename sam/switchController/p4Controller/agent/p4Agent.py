import bfrt_grpc.client as client

class P4Agent:

    def __init__(self, _addrwithport):
        self.interface = client.ClientInterface(_addrwithport, 0, 0)
        self.target = client.Target(device_id = 0, pipe_id = 0xffff)
        self.interface.bind_pipeline_config('p4nf_sam')
        self.bfrtinfo = self.interface.bfrt_info_get()

    def removeNF(self, _service_path_index, _service_index):
        # currently not supported
        pass
    
    def removeFWentry(self, _uuid):
        # currently not supported
        pass
    
    def addMonitor(self, _service_path_index, _service_index):
        pass

    def addIEGress(self, _service_path_index, _service_index):
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
            [egresstable.make_data([], 'SwitchIngress.hit_egress')]
        )
    
    def addRateLimiter(self, _service_path_index, _service_index):
        self.addMonitor(_service_path_index, _service_index)
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

    def addFW(self, _service_path_index, _service_index):
        self.addMonitor(_service_path_index, _service_index)
        # add to fw list

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
    
    def syncWithHardware(self):
        tablesync = self.bfrtinfo.table_get('SwitchIngress.CounterIngress')
        tablesync.operations_execute(self.target, 'SyncCounters')
        tablesync = self.bfrtinfo.table_get('SwitchIngress.FlowMonitor')
        tablesync.operations_execute(self.target, 'SyncCounters')
        tablesync = self.bfrtinfo.table_get('SwitchIngress.StatelessFirewallv4')
        tablesync.operations_execute(self.target, 'SyncCounters')
        tablesync = self.bfrtinfo.table_get('SwitchIngress.StatelessFirewallv6')
        tablesync.operations_execute(self.target, 'SyncCounters')
        tablesync = self.bfrtinfo.table_get('SwitchIngress.CounterEgress')
        tablesync.operations_execute(self.target, 'SyncCounters')
    
    def queryMonitor(self):
        # currently not supported
        pass
    
    def queryIOrate(self):
        # currently not supported
        pass
    
    def queryFWentry(self):
        # currently not supported
        pass
