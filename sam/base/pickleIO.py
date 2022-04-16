#!/usr/bin/python
# -*- coding: UTF-8 -*-

import base64
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

    def obj2Pickle(self, obj):
        return base64.b64encode(cPickle.dumps(obj,-1)).decode("utf-8")

    def pickle2Obj(self, pickleInstance):
        return cPickle.loads(base64.b64decode(pickleInstance))
