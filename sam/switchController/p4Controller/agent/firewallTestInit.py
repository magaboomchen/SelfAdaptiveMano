from p4Agent import P4Agent

if __name__ == '__main__':
    agent = P4Agent('192.168.100.6:50052')
    spi = 127
    si = 1
    agent.addIEGress(spi, si, 128)