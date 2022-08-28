from p4Agent import P4Agent

if __name__ == '__main__':
    agent = P4Agent('192.168.100.6:50052')
    spi = 0
    si = 2
    while True:
        opt = raw_input('Operation Code: ')
        if opt == 'E':
            break
        elif opt == 'R':
            spi += 1
            agent.addRateLimiter(spi, si)
        elif opt == 'M4':
            spi += 1
            agent.addIEGress(spi, si, 128)
            agent.addMonitorv4(spi, si)
        elif opt == 'M6':
            spi += 1
            agent.addIEGress(spi, si, 128)
            agent.addMonitorv6(spi, si)
        elif opt == 'D':
            agent.waitForDigenst()
        elif opt == 'F4':
            break
        elif opt == 'F6':
            break
        else:
            print('Invalid Opt Code.')
