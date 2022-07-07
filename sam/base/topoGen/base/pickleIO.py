#!/usr/bin/python
# -*- coding: UTF-8 -*-

import sys
if sys.version > '3':
    import _pickle as cPickle
else:
    import cPickle


class PickleIO(object):
    def __init__(self):
        pass

    def readPickleFile(self, filePath):
        df = open(filePath, 'rb')
        obj = cPickle.load(df)
        df.close()
        # self.logger.debug("obj:{0}".format(obj))
        return obj

    def writePickleFile(self, filePath, obj):
        df = open(filePath, 'wb')
        cPickle.dump(obj, df)
        df.close()
