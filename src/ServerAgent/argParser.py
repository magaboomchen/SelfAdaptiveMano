import argparse

class ArgParser():
    def __init__(self):
        parser = argparse.ArgumentParser(description='Set server agent.')
        parser.add_argument('nicPciAddress', metavar='pcia', type=str, 
            help='PCI address of the input NIC, e.g. 0000:00:08.0')
        parser.add_argument('controllNicName', metavar='cnn', type=str, 
            help='name of control nic, e.g. ens3')
        self._args = parser.parse_args()

    def getArgs(self):
        return self._args.__dict__
    
    def printArgs(self):
        logging.info("argparse.args=",self._args,type(self._args))
        d = self._args.__dict__
        for key,value in d.iteritems():
            logging.info('%s = %s'%(key,value))