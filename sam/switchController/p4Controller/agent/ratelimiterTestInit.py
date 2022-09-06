from p4Agent import P4Agent
import time

if __name__ == '__main__':
    agent = P4Agent('192.168.100.6:50052')
    spi = 1
    si = 1
    starttime = time.time()
    agent.addIEGress(spi, si, 128)
    agent.addRateLimiter(spi, si)
    agent.editRateLimiter(spi, si, 8192, 8192, 8192, 8192)
    endtime = time.time()
    print(endtime - starttime)
