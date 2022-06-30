#!/usr/bin/python
# -*- coding: UTF-8 -*-


class RateLimiterConfig(object):
    def __init__(self, maxMbps=None):
        self.maxMbps = maxMbps
