import logging
import docker

from sam.base.vnf import *
from sam.base.server import *
from sam.serverController.sffController.sibMaintainer import *

class VNFIAdder(object):
    def __init__(self, dockerPort):
        self._sibm = SIBMaintainer()
        self._dockerPort = dockerPort

    def addVNFI(self, vnfi):
        server = vnfi.node
        vdev0 = self._sibm.getVdev(vnfi.VNFIID, 0)
        vdev1 = self._sibm.getVdev(vnfi.VNFIID, 1)
        docker_url = 'tcp://%s:%d' % (server.getControlNICIP(), self._dockerPort)
        try:
            client = docker.DockerClient(base_url=docker_url, timeout=5)
        except Exception as exp:
            raise exp
        

