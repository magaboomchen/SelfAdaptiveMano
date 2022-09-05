from p4Agent import P4Agent
import time

SI_PORT_MAP = [128, 136, 144, 152, 160, 168, 176, 184, 60, 52]
if __name__ == '__main__':
    agent = P4Agent('192.168.100.6:50052')
    spi = 1
    si = 10
    starttime = time.time()
    for idx in range(10):
        agent.addIEGress(spi, si, SI_PORT_MAP[si - 1])
        agent.addMonitorv4(spi, si)
        agent.res_spi = spi
        agent.res_si = si
        agent.res_src = 0x0a000001
        agent.res_dst = 0x0a000001
        agent.addMonitorEntryv4()
        si -= 1
    endtime = time.time()
    print(endtime - starttime)
