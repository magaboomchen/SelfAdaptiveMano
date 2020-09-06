# -*- coding: UTF-8 -*-

from sam.test.FRR.dataProcessor import DataProcessor
from sam.test.FRR.plotter import Plotter


if __name__ == '__main__':
    maxPointsNum = 70

    dP = DataProcessor()
    # NotVia
    (iperf3TimeSeries, notViaDropRate) = dP.processIperf3Udp("./NotViaReMapping/iperf3udp_h2.out")
    notViaDropRate = notViaDropRate[0:maxPointsNum]
    notViaDropRate.insert(0, float("+inf"))
    notViaDropRate.insert(0, float("+inf"))
    (pingTimeSeries, icmpSeqList, notViaDelayList) = dP.processPing("./NotViaReMapping/ping_h1.out")
    notViaDelayList = dP.postProcessPing(icmpSeqList, notViaDelayList)
    notViaDelayList = notViaDelayList[0:maxPointsNum]

    # UFRR
    (iperf3TimeSeries, ufrrDropRate) = dP.processIperf3Udp("./UFRR/iperf3udp_h2.out")
    ufrrDropRate = ufrrDropRate[0:maxPointsNum]
    ufrrDropRate.insert(0, float("+inf"))
    ufrrDropRate.insert(0, float("+inf"))
    (pingTimeSeries, icmpSeqList, ufrrDelayList) = dP.processPing("./UFRR/ping_h1.out")
    ufrrDelayList = dP.postProcessPing(icmpSeqList, ufrrDelayList)
    ufrrDelayList = ufrrDelayList[0:maxPointsNum]

    # draw
    pT = Plotter()
    pT.drawDropRate([notViaDropRate, ufrrDropRate], ["NotVia + Remapping", "UFRR"], "./dropRate.pdf")
    pT.drawE2EDelay([notViaDelayList, ufrrDelayList], ["NotVia + Remapping", "UFRR"], "./delay.pdf")
