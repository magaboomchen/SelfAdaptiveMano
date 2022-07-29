#!/usr/bin/python
# -*- coding: UTF-8 -*-

import os
import sam
import sys
if sys.version > '3':
    raw_input = input
else:
    pass

SAM_MODULE_ABS_PATH = os.path.abspath(sam.__path__[0])


def screenInput(hint="Type Here: "):
    return raw_input(hint)

def x2str(obj):
    if sys.version > '3':
        return str(obj, encoding="utf-8")
    else:
        return str(obj)