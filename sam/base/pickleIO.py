#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
compatibility
https://rebeccabilbro.github.io/convert-py2-pickles-to-py3/
'''

import base64
import sys
if sys.version > '3':
    import _pickle as cPickle
else:
    import cPickle


class PickleIO(object):
    def __init__(self):
        self.defulatPickleProtocol = 2

    def readPickleFile(self, filePath):
        df = open(filePath, 'rb')
        if sys.version > '3':
            obj = cPickle.load(df, encoding="latin1")
        else:
            obj = cPickle.load(df)
        df.close()
        # self.logger.debug("obj:{0}".format(obj))
        return obj

    def writePickleFile(self, filePath, obj):
        df = open(filePath, 'wb')
        cPickle.dump(obj, df, protocol=self.defulatPickleProtocol)
        df.close()

    def obj2Pickle(self, obj):
        return base64.b64encode(cPickle.dumps(obj,
                                    protocol=self.defulatPickleProtocol
                                ))

    def pickle2Obj(self, pickleInstance):
        if sys.version > '3':
            return cPickle.loads(base64.b64decode(pickleInstance), encoding="latin1")
        else:
            return cPickle.loads(base64.b64decode(pickleInstance))
