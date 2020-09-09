#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging
import docker

from sam.base.vnf import *
from sam.base.server import *
from sam.serverController.sffController.sibMaintainer import *
from sam.serverController.vnfController.vioAllocator import *

class VNFIAdder(object):
    def __init__(self, dockerPort):
        self._sibm = SIBMaintainer()
        self._dockerPort = dockerPort

    def addVNFI(self, vnfi, vioStart):  
        server = vnfi.node
        docker_url = 'tcp://%s:%d' % (server.getControlNICIP(), self._dockerPort)
        client = docker.DockerClient(base_url=docker_url, timeout=5)

        vnfiType = vnfi.VNFType
        if vnfiType == VNF_TYPE_FORWARD:  # add testpmd
            return self._addTestpmd(vnfi, client, vioStart)
        else:
            # TODO
            pass

    def _containerCommand(self, appName, vnfi, vioStart):
        
        startCPU = 0 # TODO:?
        endCPU = vnfi.maxCPUNum - 1

        _vdev0 = self._sibm.getVdev(vnfi.VNFIID, 0).split(',')
        _vdev1 = self._sibm.getVdev(vnfi.VNFIID, 1).split(',')
        vdev0 = '%s,path=%s' % ('net_virtio_user%d' % vioStart, _vdev0[1][6:])
        vdev1 = '%s,path=%s' % ('net_virtio_user%d' % (vioStart + 1) , _vdev1[1][6:])
        command = "%s -l %d-%d -n 1 -m %d --no-pci --vdev=%s --vdev=%s " % (appName, startCPU, endCPU, vnfi.maxMem, vdev0, vdev1) +\
                  '--file-prefix=virtio --log-level=8 -- --txqflags=0xf00 --disable-hw-vlan ' +\
                  '--forward-mode=io --port-topology=chained --total-num-mbufs=2048 -a' 
        return command

    def _addTestpmd(self, vnfi, client, vioStart):
        imageName = 'dpdk-app-testpmd'
        appName = './x86_64-native-linuxapp-gcc/app/testpmd'
        command = self._containerCommand(appName, vnfi, vioStart)
        logging.info(command)
        containerName = 'vnf-%s' % vnfi.VNFIID 
        container = client.containers.run(imageName, command, tty=True, remove=True, privileged=True, name=containerName, 
            volumes={'/mnt/huge_1GB': {'bind': '/dev/hugepages', 'mode': 'rw'}, '/tmp/': {'bind': '/tmp/', 'mode': 'rw'}}, detach=True)
        con = client.containers.get(container.id)
        logging.info(con.name)
        return container.id

        
