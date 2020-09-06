

class DataProcessor(object):
    def __init__(self):
        self.f = None

    def processIperf3(self, path):
        timePointList = []
        throughputList = []
        try:
            self.f = open(path, 'r')
            for line in self.f.readlines():
                if line.find("sec") != -1 and line.find("sender") == -1 and\
                    line.find("receiver") == -1:
                    timePoint = float(line.split("-")[0].split("]")[1])
                    # print("timePoint:{0}".format(timePoint))
                    timePointList.append(timePoint)

                    throughputWithUnit = line.split("Bytes")[1].split("bits")[0]
                    unit = throughputWithUnit[-1]
                    throughput = float(throughputWithUnit[:-2])
                    if unit == " ":
                        throughput = throughput * 0.001 * 0.001
                    elif unit == "K":
                        throughput = throughput * 0.001
                    elif unit == "M":
                        pass
                    else:
                        raise ValueError(
                            "DataProcessor: iperf3 unknown throughtput unit"
                            " {0}".format(unit))
                    # print("\t\tthroughput:{0}".format(throughput))
                    throughputList.append(throughput)
        finally:
            if self.f:
                self.f.close()
        return (timePointList, throughputList)

    def processIperf3Udp(self, path):
        timePointList = []
        dropRateList = []
        
        try:
            self.f = open(path, 'r')
            for line in self.f.readlines():
                if line.find("%)") != -1:
                    timePoint = float(line.split("-")[0].split("]")[1])
                    # print("timePoint:{0}".format(timePoint))
                    timePointList.append(timePoint)

                    dropRateString = line.split("(")[1].split("%)")[0]
                    if dropRateString == "-nan":
                        print("Get -nan in files")
                        # dropRate = float("+inf")
                        dropRate = 100.0
                    else:
                        dropRate = float(dropRateString)
                    # print("\t\tdropRate:{0}".format(dropRate))
                    dropRateList.append(dropRate)
                else:
                    pass
            timePointList.pop()
            dropRateList.pop()
        finally:
            if self.f:
                self.f.close()
        return (timePointList, dropRateList)

    def processPing(self, path):
        timePointList = []
        icmpSeqList = []
        delayList = []
        try:
            self.f = open(path, 'r')
            count = 0
            for line in self.f.readlines():
                if line.find("ms") != -1:
                    timePoint = 0.1 * count
                    
                    # print("timePoint:{0}".format(timePoint))
                    timePointList.append(timePoint)

                    icmpSeq = int(line.split("icmp_seq=")[1].split(" ttl=")[0])
                    icmpSeqList.append(icmpSeq)

                    delay = float(line.split("time=")[1].split(" ")[0])
                    unit = line.split("time=")[1].split(" ")[1].strip("\n")

                    if unit == "us":
                        delay = delay * 0.001
                    elif unit == "ms":
                        delay = delay
                    elif unit == "s":
                        delay = delay * 1000
                    else:
                        raise ValueError(
                            "DataProcessor: ping unknown delay unit"
                            " {0}".format(unit))
                    # print("\t\tdelay:{0}".format(delay))
                    delayList.append(delay)

                elif line.find("Destination Host Unreachable") != -1:
                    timePointList.append(timePoint)
                    icmpSeq = int(line.split("icmp_seq=")[1].split(" Destination Host Unreachable")[0])
                    icmpSeqList.append(icmpSeq)
                    delayList.append(float("+inf"))
                else:
                    pass
                count = count + 1
        finally:
            if self.f:
                self.f.close()
        return (timePointList, icmpSeqList, delayList)

    def postProcessPing(self, icmpSeqList, delayList):
        newDelayList = []
        maxIcmpSeq = icmpSeqList[-1]
        count = 1
        while True:
            if count in icmpSeqList:
                index = icmpSeqList.index(count)
                icmpSeq = delayList[index]
                newDelayList.append(icmpSeq)
            else:
                newDelayList.append(float("+inf"))
            count = count + 1

            if count == maxIcmpSeq:
                break
        return newDelayList
