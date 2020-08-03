import argparse

class ArgParserBase(object):
    def __init__(self):
        pass

    def getArgs(self):
        return self.args.__dict__
    
    def printArgs(self):
        logging.info("argparse.args=",self.args,type(self.args))
        d = self.args.__dict__
        for key,value in d.iteritems():
            logging.info('%s = %s'%(key,value))