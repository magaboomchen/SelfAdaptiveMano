#!/usr/bin/python
# -*- coding: UTF-8 -*-

import docker

from sam.base.vnf import *
from sam.base.server import *
from sam.serverController.vnfController.sourceAllocator import *
from sam.serverController.vnfController.vcConfig import vcConfig


class VNFIDeleter(object):
    def __init__(self, dockerPort):
        self._dockerPort = dockerPort
    
    def deleteVNFI(self, vnfiDS, vioAllo, cpuAllo):
        if vnfiDS.error is not None:  # this vnfi is not sucessfully deployed
            assert vnfiDS.containerID is None
            return
        vioAllo.freeSource(vnfiDS.vioStart, 2)
        cpuAllo.freeCPU(vnfiDS.cpus)
        server = vnfiDS.vnfi.node
        ''' kill container '''        
        docker_url = 'tcp://%s:%d' % (server.getControlNICIP(), self._dockerPort)
        client = docker.DockerClient(base_url=docker_url, timeout=5)
        containerID = vnfiDS.containerID
        try:
            container = client.containers.get(containerID)
            container.kill()
        except:
            return