from sam.serverController.bessGRPC import *

class SFCDeleter(BessGRPC): # TODO: 将此接口改在内部
    def __init__(self,clsMaintainer):
        self.clsMaintainer = clsMaintainer

    def delSFC(self,cmd):
        pass

