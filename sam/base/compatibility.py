#!/usr/bin/python
# -*- coding: UTF-8 -*-

import sys
if sys.version > '3':
    raw_input = input
else:
    pass

def screenInput(hint="Type Here: "):
    raw_input(hint)