class SLO(object):
    def __init__(self, availability=None, latencyBound=None, throughput=None, dropRate=None):
        self.availability = availability
        self.latencyBound = latencyBound
        self.throughput =throughput
        self.dropRate = dropRate