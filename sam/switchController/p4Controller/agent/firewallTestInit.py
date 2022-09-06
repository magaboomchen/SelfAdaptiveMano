from p4Agent import P4Agent
import time

if __name__ == '__main__':
    agent = P4Agent('192.168.100.6:50052')
    spi = 1
    si = 1
    starttime = time.time()
    agent.addIEGress(spi, si, 128)
    agent.addv4FWentry(
        _service_path_index = spi,
        _service_index = si,
        _src_addr = '10.0.0.1',
        _dst_addr = '10.0.0.1',
        _src_mask = '255.255.255.255',
        _dst_mask = '255.255.255.255',
        _nxt_hdr = 6, # TCP
        _priority = 0,
        _is_drop = True
    )
    agent.addv4FWentry(
        _service_path_index = spi,
        _service_index = si,
        _src_addr = '10.0.0.1',
        _dst_addr = '10.0.0.1',
        _src_mask = '255.255.255.255',
        _dst_mask = '255.255.255.255',
        _nxt_hdr = 17, # UDP
        _priority = 0,
        _is_drop = True
    )
    endtime = time.time()
    print(endtime - starttime)
