from sam.serverController.bessGRPC import *

class SFCDeleter(BessGRPC):
    def __init__(self,clsMaintainer):
        self.clsMaintainer = clsMaintainer

    def delSFC(self,cmd):
        pass

