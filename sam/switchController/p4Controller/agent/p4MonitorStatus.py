import time

from sam.base.routingMorphic import IPV4_ROUTE_PROTOCOL
from sam.base.routingMorphic import IPV6_ROUTE_PROTOCOL
from sam.base.routingMorphic import SRV6_ROUTE_PROTOCOL
from sam.base.routingMorphic import ROCEV1_ROUTE_PROTOCOL
from sam.base.sfc import SFC_DIRECTION_0, SFC_DIRECTION_1
from sam.base.monitorStatistic import MonitorStatistics, SrcDstPair

class P4MonitorStat:
    def __init__(self, _src_addr, _dst_addr, _pkt_rate, _byte_rate):
        self.src = _src_addr
        self.dst = _dst_addr
        self.pktrate = _pkt_rate
        self.byterate = _byte_rate

class P4MonitorEntry:
    def __init__(self, _uuid, _src_addr, _dst_addr):
        self.uuid = _uuid
        self.src = _src_addr
        self.dst = _dst_addr

class P4MonitorStatus:
    def __init__(self, _service_path_index, _service_index, _proto, _p4id):
        self.p4id = _p4id
        self.service_path_index = _service_path_index
        self.service_index = _service_index
        self.proto = _proto
        self._entries = {}
        self._src = []
        self._dst = []
        self._cnt = 0
        self._pkts = []
        self._bytes = []
        self._time = []
        self._pktrate = []
        self._byterate = []
    
    def addEntry(self, _src_addr, _dst_addr):
        self._cnt += 1
        self._entries[self._cnt] = True
        self._src.append(_src_addr)
        self._dst.append(_dst_addr)
        self._pkts.append(0)
        self._bytes.append(0)
        self._time.append(time.time())
        self._pktrate.append(0.0)
        self._byterate.append(0.0)
    
    def removeEntry(self, _uuid):
        self._entries[_uuid] = False
    
    def updateStat(self, _uuid, _pkt_cnt, _byte_cnt, _time):
        self._pktrate[_uuid] = (_pkt_cnt - self._pkts[_uuid]) / (_time - self._time[_uuid])
        self._byterate[_uuid] = (_byte_cnt - self._bytes[_uuid]) / (_time - self._time[_uuid])
        self._time[_uuid] = _time
        self._pkts[_uuid] = _pkt_cnt
        self._bytes[_uuid] = _byte_cnt
    
    def getEntryList(self):
        res = []
        for i in self._entries.keys():
            if self._entries[i]:
                res.append(P4MonitorEntry(
                    _uuid = i,
                    _src_addr = self._src[i],
                    _dst_addr = self._dst[i]
                ))
        return res
    
    def getStat(self):
        res = []
        for i in self._entries.keys():
            if self._entries[i]:
                res.append(P4MonitorStat(
                    _src_addr = self._src[i],
                    _dst_addr = self._dst[i],
                    _pkt_rate = self._pktrate[i],
                    _byte_rate = self._byterate[i]
                ))
        return res
    
    def hasEntry(self, _src_addr, _dst_addr):
        for i in self._entries.keys():
            if self._entries[i]:
                if _src_addr == self._src[i] and _dst_addr == self._dst[i]:
                    return True
        return False
