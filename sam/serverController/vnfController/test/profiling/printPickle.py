#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging
from scapy.all import *
import time

from sam.base.pickleIO import PickleIO

if __name__ == "__main__":
    pass

    pIO = PickleIO()
    res = pIO.readPickleFile("./deployTimeRes.pickle")
    print(res)