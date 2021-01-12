#!/usr/bin/python
# -*- coding: UTF-8 -*-

import os
import pickle
import base64


class PickleIO(object):
    def __init__(self):
        pass

    def readPickleFile(self, filePath):
        df = open(filePath, 'rb')
        obj = pickle.load(df)
        df.close()
        # self.logger.debug("obj:{0}".format(obj))
        return obj

    def writePickleFile(self, filePath, obj):
        df = open(filePath, 'wb')
        pickle.dump(obj, df)
        df.close()
