from p4Agent import P4Agent

if __name__ == '__main__':
    agent = P4Agent('192.168.100.4:50052')
    spi = 0
    si = 0
    while True:
        opt = raw_input('Operation Code: ')
        if opt == 'E':
            break
        elif opt == 'R':
            spi += 1
            si += 1
            agent.addRateLimiter(spi, si)
        elif opt == 'M':
            spi += 1
            si += 1
            agent.addMonitor(spi, si)
        elif opt == 'F4':
            break
        elif opt == 'F6':
            break
        else:
            print('Invalid Opt Code.')
