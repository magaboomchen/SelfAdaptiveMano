from p4Agent import P4Agent
import time

if __name__ == '__main__':
    agent = P4Agent('192.168.100.6:50052')
    spi = 1
    si = 1
    starttime = time.time()
    agent.addIEGress(spi, si, 128)
    agent.addMonitorv4(spi, si)
    agent.res_spi = spi
    agent.res_si = si
    agent.res_src = 0x0a000001
    agent.res_dst = 0x0a000001
    agent.addMonitorEntryv4()
    endtime = time.time()
    print(endtime - starttime)
