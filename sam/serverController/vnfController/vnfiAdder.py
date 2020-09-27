#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging
import docker

from sam.base.vnf import *
from sam.base.server import *
from sam.serverController.sffController.sibMaintainer import *
from sam.serverController.vnfController.sourceAllocator import *

DEFAULT_FASTCLICK = True
DEBUG = False  # if you set debug=True, the container will not be removed even if the app is terminated.
               # !!!please run docker rm XXX to free resources of the container.!!!

class VNFIAdder(object):
    def __init__(self, dockerPort):
        self._sibm = SIBMaintainer()
        self._dockerPort = dockerPort

    def addVNFI(self, vnfi, vioAllo, cpuAllo):  
        server = vnfi.node
        docker_url = 'tcp://%s:%d' % (server.getControlNICIP(), self._dockerPort)
        client = docker.DockerClient(base_url=docker_url, timeout=5)

        vnfiType = vnfi.VNFType
        if vnfiType == VNF_TYPE_FORWARD:  # add testpmd
            return self._addTestpmd(vnfi, client, vioAllo, cpuAllo)
        else:
            # TODO
            pass

    def _addTestpmd(self, vnfi, client, vioAllo, cpuAllo, useFastClick=False, debug=True):
        startCPU = cpuAllo.allocateSource(vnfi.maxCPUNum)
        endCPU = startCPU + vnfi.maxCPUNum - 1
        vioStart = vioAllo.allocateSource(2)
        _vdev0 = self._sibm.getVdev(vnfi.VNFIID, 0).split(',')
        _vdev1 = self._sibm.getVdev(vnfi.VNFIID, 1).split(',')
        vdev0 = '%s,path=%s' % ('net_virtio_user%d' % vioStart, _vdev0[1][6:])
        vdev1 = '%s,path=%s' % ('net_virtio_user%d' % (vioStart + 1) , _vdev1[1][6:])
        if not useFastClick:
            imageName = 'dpdk-app-testpmd'
            appName = './x86_64-native-linuxapp-gcc/app/testpmd'
            command = "%s -l %d-%d -n 1 -m %d --no-pci --vdev=%s --vdev=%s " % (appName, startCPU, endCPU, vnfi.maxMem, vdev0, vdev1) +\
                  '--file-prefix=virtio --log-level=8 -- --txqflags=0xf00 --disable-hw-vlan ' +\
                  '--forward-mode=io --port-topology=chained --total-num-mbufs=2048 -a' 
        else:
            imageName = 'fastclick'
            appName = './test-dpdk.click'
            command = "./fastclick/bin/click --dpdk -l %d-%d -n 1 -m %d --no-pci --vdev=%s --vdev=%s -- %s" % (startCPU, endCPU, vnfi.maxMem, vdev0, vdev1, appName)
        logging.info(command)
        containerName = 'vnf-%s' % vnfi.VNFIID 
        try:
            container = client.containers.run(imageName, command, tty=True, remove=not debug, privileged=True, name=containerName, 
                volumes={'/mnt/huge_1GB': {'bind': '/dev/hugepages', 'mode': 'rw'}, '/tmp/': {'bind': '/tmp/', 'mode': 'rw'}}, detach=True)
            logging.info(container.logs())
        except Exception as e:
            # free allocated CPU and virtioID
            cpuAllo.freeSource(startCPU, vnfi.maxCPUNum)
            vioAllo.freeSource(vioStart, 2)
            raise e
        return container.id, startCPU, vioStart

        
