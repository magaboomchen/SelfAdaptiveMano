#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.pickleIO import PickleIO
from sam.base.compatibility import screenInput


if __name__ == "__main__":
    pIO = PickleIO()
    topologyDict = pIO.readPickleFile("./topology/fat-tree-turbonet/0/fat-tree-k=4_V=2_M=100.M=100.pickle")
    for key,value in topologyDict.items():
        screenInput()
        print(key)
        print(value)