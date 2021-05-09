import pickle
import pandas as pd
import numpy as np
import os

numCores=12
numSockets=2
store_columns = ["TIME(ticks)", "EXEC", "IPC", "FREQ", "AFREQ", "L3MISS", "L2MISS", "L3HIT", "L2HIT", "L3MPI", "L2MPI", "L3OCC", "LMB", "RMB", "READ", "WRITE"]
model_columns = ["EXEC", "IPC", "FREQ", "AFREQ", "L3MISS", "L2MISS", "L3HIT", "L2HIT", "L3MPI", "L2MPI", "L3OCC", "LMB", "RMB", "READ", "WRITE"]

self_location=os.path.dirname(os.path.abspath(__file__))
cont_dict = pickle.load(open(os.path.join(self_location, 'contention_dictionary.p'), 'rb'))
sens_models = pickle.load(open(os.path.join(self_location, 'sensitivity_dictionary.p'), 'rb'))

class NF:
    def __init__(self, nf, pkt, flow_count):
        self.nf=nf
        self.pkt=pkt
        self.flow_count=flow_count

def predict(target:NF, competing:NF):
    nr_competitors = len(competing)

    if nr_competitors==0:
        return np.average(sens_models[target.nf, target.pkt, target.flow_count]['solo'])

    aggregate_cont = pd.DataFrame(columns=store_columns)
    for cNF in competing:
        vector = cont_dict[(cNF.nf, cNF.pkt, cNF.flow_count)]
        cNF_cont = vector[nr_competitors].median()
        aggregate_cont = aggregate_cont.append(cNF_cont,ignore_index=True)

    composed_cont = pd.Series(index=model_columns, dtype=np.float64)
    # EXEC avg
    composed_cont.EXEC=aggregate_cont.EXEC.sum()/(numCores/numSockets)
    # IPC =EXEC/FREQ
    # FREQ avg
    composed_cont.FREQ=aggregate_cont.FREQ.sum()/(numCores/numSockets)
    composed_cont.IPC=composed_cont.EXEC/composed_cont.FREQ
    # AFREQ: FREQ/AFREQ=avg
    composed_cont.AFREQ=composed_cont.FREQ/((aggregate_cont.FREQ/aggregate_cont.AFREQ).sum()/(numCores/numSockets))
    # L3MISS sum
    composed_cont.L3MISS=aggregate_cont.L3MISS.sum()
    # L2MISS sum
    composed_cont.L2MISS=aggregate_cont.L2MISS.sum()
    # L3HIT: L3MISS/(1-L3HIT)=sum
    composed_cont.L3HIT=1-composed_cont.L3MISS/((aggregate_cont.L3MISS/(1-aggregate_cont.L3HIT)).sum())
    # L2HIT: L2MISS/(1-L2HIT)=sum
    composed_cont.L2HIT=1-composed_cont.L2MISS/((aggregate_cont.L2MISS/(1-aggregate_cont.L2HIT)).sum())
    # L3MPI =L3MISS/(EXEC*#core)/sys.TIME_TICK
    composed_cont.L3MPI=composed_cont.L3MISS/((aggregate_cont.EXEC*aggregate_cont['TIME(ticks)']).sum())
    # L2MPI =L2MISS/(EXEC*#core)/sys.TIME_TICK
    composed_cont.L2MPI=composed_cont.L2MISS/((aggregate_cont.EXEC*aggregate_cont['TIME(ticks)']).sum())
    # L3OCC sum
    composed_cont.L3OCC=aggregate_cont.L3OCC.sum()
    # LMB sum
    composed_cont.LMB=aggregate_cont.LMB.sum()
    # RMB sum?
    composed_cont.RMB=aggregate_cont.RMB.sum()
    composed_cont.READ=aggregate_cont.READ.sum()
    composed_cont.WRITE=aggregate_cont.WRITE.sum()

    composed_cont = pd.DataFrame(composed_cont.values.reshape(1,-1), columns=model_columns)

    model = sens_models[target.nf, target.pkt, target.flow_count]['slomo']
    result = model.predict(composed_cont)[0]
    return result

while True:
    competingN=int(input())
    nflist=[]
    for i in range(competingN+1):
        params=input().split()
        nf=params[0]
        pkt=int(params[1])
        flow_count=int(params[2])
        nflist.append(NF(nf,pkt,flow_count))
    print(predict(nflist[0],nflist[1:]))
