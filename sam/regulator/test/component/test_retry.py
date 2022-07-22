#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
This is an example for writing integrate test
The work flow:
    * generate 1 addSFC and 1 addSFCI command to dispatcher

Usage of this unit test:
    python -m pytest ./test_retry.py -s --disable-warnings
'''

from sam.test.testBase import TestBase

MANUAL_TEST = True


class TestNoticeClass(TestBase):
    # TODO
    # It's not a mandatory features!!!
    pass
