#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.pickleIO import PickleIO


if __name__ == "__main__":
    pIO = PickleIO()
    res = pIO.readPickleFile("./deployTimeRes.pickle")
    print(res)