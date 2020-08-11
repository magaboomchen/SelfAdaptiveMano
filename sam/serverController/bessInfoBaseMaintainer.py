# TODO : test

class BessInfoBaseMaintainer(object):
    def __init__(self):
        self._modules = {}
        self._links = {}

    def addModule(self,name,mclass):
        self._modules[name] = {'mclass':mclass,
            'rules':[],'ogates':{}}
        # 'ogates': {key:ogateNum}
        # key <- sfcUUID or SFCIID

    def delModule(self,name):
        if name in self._modules.iterkeys():
            del self._modules[name]

    def getModule(self,name):
        if name in self._modules.iterkeys():
            return self._modules[name]
        else:
            return None

    # def addRule(self,name,rule):
    #     self._modules[name]['rules'].append(rule)

    # def delRule(self,name,rule):
    #     self._modules[name]['rules'].remove(rule)

    # def getRules(self,name):
    #     return self._modules[name]['rules']

    # def addLink(self,m1,ogate,m2,igate):
    #     self._links[(m1,ogate)] = (m2,igate)

    # def delLink(self,m1,ogate):
    #     if (m1,ogate) in self._links.iterkeys():
    #         del self._links[(m1,ogate)]

    # def getLink(self,m1,ogate):
    #     if (m1,ogate) in self._links.iterkeys():
    #         return self._links[(m1,ogate)]
    #     else:
    #         return None

    def genAvailableMiniNum4List(self,numList):
        if numList == []:
            return 0
        numList.sort()
        maxNum = max(numList)
        minNum = min(numList)
        if minNum != 0:
            return 0
        for i in range(len(numList)-1):
            currentNum = numList[i]
            nextNum = numList[i+1]
            if nextNum-currentNum > 1:
                return currentNum + 1
        else:
            return maxNum+1

    def getModuleOGateNumList(self,moduleName):
        ogates = self._modules[moduleName]['ogates']
        oGatesList = []
        for ogate in ogates.itervalues():
            oGatesList.append(ogate)
        return oGatesList

    def addOGate2Module(self,moduleName,key,oGateNum):
        ogates = self._modules[moduleName]['ogates']
        ogates[key] = oGateNum

    def getModuleOGate(self,moduleName,key):
        ogates = self._modules[moduleName]['ogates']
        return ogates[key]

    def delModuleOGate(self,moduleName,key):
        ogates = self._modules[moduleName]['ogates']
        del ogates[key]