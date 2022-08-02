#!/usr/bin/python
# -*- coding: UTF-8 -*-

SWITCH_MAX_NF_MONITOR = 5
SWITCH_MAX_NF_FW_IPV4_ENTRIES = 3000
SWITCH_MAX_NF_FW_IPV6_ENTRIES = 3000
SWITCH_MAX_NF_RATELIMITER = 500
SWITCH_MAX_SFCI = 500


class P4NFUsage(object):
    def __init__(self):
        # type: () -> None
        self.monitorNumUsage = 0
        self.fwV4NumUsage = 0
        self.fwV6NumUsage = 0
        self.rateLimiterNumUsage = 0
        self.sfciUsage = 0
        self.bandwidthUsage = 0

    def reserveMonitor(self, num):
        # type: (int) -> None
        self.monitorNumUsage += num
        self.sfciUsage += num

    def reserveRatelimiter(self, num):
        # type: (int) -> None
        self.rateLimiterNumUsage += num
        self.sfciUsage += num

    def reserveV4Firewall(self, num):
        # type: (int) -> None
        self.fwV4NumUsage += num
        self.sfciUsage += num

    def reserveV6Firewall(self, num):
        # type: (int) -> None
        self.fwV6NumUsage += num
        self.sfciUsage += num

    def releaseMonitor(self, num):
        # type: (int) -> None
        self.monitorNumUsage -= num
        self.sfciUsage -= num

    def releaseRatelimiter(self, num):
        # type: (int) -> None
        self.rateLimiterNumUsage -= num
        self.sfciUsage -= num

    def releaseV4Firewall(self, num):
        # type: (int) -> None
        self.fwV4NumUsage -= num
        self.sfciUsage -= num

    def releaseV6Firewall(self, num):
        # type: (int) -> None
        self.fwV6NumUsage -= num
        self.sfciUsage -= num

    def hasEnoughMonitorResource(self, num):
        # type: (int) -> bool
        return (self.monitorNumUsage + num 
                    <= SWITCH_MAX_NF_MONITOR
                and self.sfciUsage + num 
                    <= SWITCH_MAX_SFCI)

    def hasEnoughRatelimiterResource(self, num):
        # type: (int) -> bool
        return (self.rateLimiterNumUsage + num 
                    <= SWITCH_MAX_NF_MONITOR
                and self.sfciUsage + num 
                    <= SWITCH_MAX_SFCI)

    def hasEnoughV4FirewallResource(self, num):
        # type: (int) -> bool
        return (self.fwV4NumUsage + num 
                    <= SWITCH_MAX_NF_FW_IPV4_ENTRIES
                and self.sfciUsage + num 
                    <= SWITCH_MAX_SFCI)

    def hasEnoughV6FirewallResource(self, num):
        # type: (int) -> bool
        return (self.fwV6NumUsage + num 
                    <= SWITCH_MAX_NF_FW_IPV6_ENTRIES
                and self.sfciUsage + num 
                    <= SWITCH_MAX_SFCI)
    
    def hasEnoughSFCINumResource(self, num):
        # type: (int) -> bool
        return self.sfciUsage + num <= SWITCH_MAX_SFCI