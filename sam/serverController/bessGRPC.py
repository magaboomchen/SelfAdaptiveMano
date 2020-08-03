import logging

class BessGRPC(object):
    def _checkResponse(self,response):
        if response.error.code != 0:
            logging.error( str(response.error) )
            raise ValueError('bess cmd failed.')