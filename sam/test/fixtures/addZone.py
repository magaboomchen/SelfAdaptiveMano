#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.dashboard.dashboardInfoBaseMaintainer import DashboardInfoBaseMaintainer


if __name__ == "__main__":
    dib = DashboardInfoBaseMaintainer("localhost", "dbAgent", "123")
    dib.addZone(" ")
    dib.addZone("SIMULATOR_ZONE")
    dib.addZone("MININET_ZONE")
    dib.addZone("TURBONET_ZONE")

    dib.delZone("MININET_ZONE")
    dib.delZone("TURBONET_ZONE")

    zoneNameList = dib.getAllZone()
