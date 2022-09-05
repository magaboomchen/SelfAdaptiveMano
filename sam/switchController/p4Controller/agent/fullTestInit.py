from p4Agent import P4Agent
import time

if __name__ == '__main__':
    agent = P4Agent('192.168.100.6:50052')
    spi = 2
    si = 1
    starttime = time.time()
    print(starttime)
    for i in range(1000):
        spi += 1
        agent.addIEGress(spi, si, 128)
        agent.addRateLimiter(spi, si)
        agent.editRateLimiter(spi, si, 8192, 8192, 8192, 8192)
    spi += 1
    agent.addIEGress(spi, si, 128)
    for i in range(3000):
        agent.addv4FWentry(
            _service_path_index = spi,
            _service_index = si,
            _src_addr = '10.0.' + str((i >> 8)) + '.' + str((i & 255)),
            _dst_addr = '10.0.0.1',
            _src_mask = '255.255.255.255',
            _dst_mask = '255.255.255.255',
            _nxt_hdr = 6,
            _priority = 0,
            _is_drop = False
        )
    spi += 1
    agent.addIEGress(spi, si, 128)
    for i in range(3000):
        agent.addv6FWentry(
            _service_path_index = spi,
            _service_index = si,
            _src_addr = '::' + str(i),
            _dst_addr = '::' + str(i),
            _src_mask = 'ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff',
            _dst_mask = 'ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff',
            _nxt_hdr = 6,
            _priority = 0,
            _is_drop = False
        )
    spi += 1
    agent.addIEGress(spi, si, 128)
    agent.addMonitorv4(spi, si)
    for i in range(3000):
        agent.res_spi = spi
        agent.res_si = si
        agent.res_src = i
        agent.res_dst = i
        agent.addMonitorEntryv4()
    spi += 1
    agent.addIEGress(spi, si, 128)
    agent.addMonitorv6(spi, si)
    for i in range(3000):
        agent.res_spi = spi
        agent.res_si = si
        agent.res_src = i
        agent.res_dst = i
        agent.addMonitorEntryv6()
    endtime = time.time()
    spi = 1
    agent.addIEGress(spi, si, 128)
    agent.addMonitorv4(spi, si)
    agent.res_spi = spi
    agent.res_si = si
    agent.res_src = 0x0a000001
    agent.res_dst = 0x0a000001
    agent.addMonitorEntryv4()
    print(endtime)
    print(endtime - starttime)
