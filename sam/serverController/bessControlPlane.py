import logging
from sam.base.socketConverter import SocketConverter

class BessControlPlane(object):
    def __init__(self):
        self._sc = SocketConverter()

    def _checkResponse(self,response):
        if response.error.code != 0:
            logging.error( str(response.error) )
            raise ValueError('bess cmd failed.')

    def _getWM2Rule(self,match):
        values=[
            {"value_bin":b'\x00'},
            {"value_bin":b'\x00\x00\x00\x00\x00\x00\x00\x00'},
            {"value_bin":b'\x00\x00\x00\x00\x00\x00\x00\x00'},
            {"value_bin":b'\x00\x00'},
            {"value_bin":b'\x00\x00'}
        ]
        masks=[
            {'value_bin':b'\x00'},
            {'value_bin':b'\x00\x00\x00\x00\x00\x00\x00\x00'},
            {'value_bin':b'\x00\x00\x00\x00\x00\x00\x00\x00'},
            {'value_bin':b'\x00\x00'},
            {'value_bin':b'\x00\x00'}
        ]
        if match['proto'] != None:
            values[0]["value_bin"] = match['proto']
            masks[0]["value_bin"] = b'\xFF'
        if match['srcIP'] != None:
            values[1]["value_bin"] = self._sc.aton(match['srcIP'])
            masks[1]["value_bin"] = b'\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF'
        if match['dstIP'] != None:
            values[2]["value_bin"] = self._sc.aton(match['dstIP'])
            masks[2]["value_bin"] = b'\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF'
        if match['srcPort'] != None:
            values[3]["value_bin"] = self._sc.aton(match['srcPort'])
            masks[3]["value_bin"] = b'\xFF\xFF\xFF\xFF'
        if match['dstPort'] != None:
            values[4]["value_bin"] = self._sc.aton(match['dstPort'])
            masks[4]["value_bin"] = b'\xFF\xFF\xFF\xFF'
        return [values,masks]