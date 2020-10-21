#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging
import docker

from sam.base.vnf import *
from sam.base.server import *
from sam.base.acl import *
from sam.base.lb import *
from sam.serverController.sffController.sibMaintainer import *
from sam.serverController.vnfController.sourceAllocator import *
from sam.serverController.vnfController.vcConfig import vcConfig

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
            return self._addFWD(vnfi, client, vioAllo, cpuAllo)
        elif vnfiType == VNF_TYPE_FW:
            return self._addFW(vnfi, client, vioAllo, cpuAllo)
        elif vnfiType == VNF_TYPE_LB:
            return self._addLB(vnfi, client, vioAllo, cpuAllo)

    def _addFWD(self, vnfi, client, vioAllo, cpuAllo, useFastClick=vcConfig.DEFAULT_FASTCLICK, debug=vcConfig.DEBUG):
        startCPU = cpuAllo.allocateSource(vnfi.maxCPUNum)
        endCPU = startCPU + vnfi.maxCPUNum - 1
        vioStart = vioAllo.allocateSource(2)
        _vdev0 = self._sibm.getVdev(vnfi.VNFIID, 0).split(',')
        _vdev1 = self._sibm.getVdev(vnfi.VNFIID, 1).split(',')
        vdev0 = '%s,path=%s' % ('net_virtio_user%d' % vioStart, _vdev0[1][6:])
        vdev1 = '%s,path=%s' % ('net_virtio_user%d' % (vioStart + 1) , _vdev1[1][6:])
        if not useFastClick:
            imageName = vcConfig.FWD_IMAGE_DPDK
            appName = vcConfig.FWD_APP_DPDK
            command = "%s -l %d-%d -n 1 -m %d --no-pci --vdev=%s --vdev=%s " % (appName, startCPU, endCPU, vnfi.maxMem, vdev0, vdev1) +\
                  '--file-prefix=virtio --log-level=8 -- --txqflags=0xf00 --disable-hw-vlan ' +\
                  '--forward-mode=io --port-topology=chained --total-num-mbufs=2048 -a' 
        else:
            imageName = vcConfig.FWD_IMAGE_CLICK
            appName = vcConfig.FWD_APP_CLICK
            command = "./fastclick/bin/click --dpdk -l %d-%d -n 1 -m %d --no-pci --vdev=%s --vdev=%s -- %s" % (startCPU, endCPU, vnfi.maxMem, vdev0, vdev1, appName)
        logging.info(command)
        containerName = 'vnf-%s' % vnfi.VNFIID 
        try:
            volumes = {'/mnt/huge_1GB': {'bind': '/dev/hugepages', 'mode': 'rw'}, '/tmp/': {'bind': '/tmp/', 'mode': 'rw'}}
            container = client.containers.run(imageName, command, tty=True, remove=not debug, privileged=True, name=containerName, 
                volumes=volumes, detach=True)
            #logging.info(container.logs())
        except Exception as e:
            # free allocated CPU and virtioID
            cpuAllo.freeSource(startCPU, vnfi.maxCPUNum)
            vioAllo.freeSource(vioStart, 2)
            raise e
        return container.id, startCPU, vioStart

    def _addFW(self, vnfi, client, vioAllo, cpuAllo, debug=vcConfig.DEBUG):
        ACL = vnfi.config['ACL']        
        startCPU = cpuAllo.allocateSource(vnfi.maxCPUNum)
        endCPU = startCPU + vnfi.maxCPUNum - 1
        vioStart = vioAllo.allocateSource(2)
        _vdev0 = self._sibm.getVdev(vnfi.VNFIID, 0).split(',')
        _vdev1 = self._sibm.getVdev(vnfi.VNFIID, 1).split(',')
        vdev0 = '%s,path=%s' % ('net_virtio_user%d' % vioStart, _vdev0[1][6:])
        vdev1 = '%s,path=%s' % ('net_virtio_user%d' % (vioStart + 1) , _vdev1[1][6:])
        imageName = vcConfig.FW_IMAGE_CLICK
        appName = vcConfig.FW_APP_CLICK
        containerName = 'vnf-%s' % vnfi.VNFIID 
        try:
            command = 'mkdir %s' % vcConfig.FW_RULE_DIR
            for rule in ACL:
                command = command + ' && echo \"%s\" >> %s' % (rule.genFWLine(), vcConfig.FW_RULE_PATH)
            command = command + ' && ./fastclick/bin/click --dpdk -l %d-%d -n 1 -m %d --no-pci --vdev=%s --vdev=%s -- %s' % (startCPU, endCPU, vnfi.maxMem, vdev0, vdev1, appName)
            #logging.info(command)
            volumes = {'/mnt/huge_1GB': {'bind': '/dev/hugepages', 'mode': 'rw'}, '/tmp/': {'bind': '/tmp/', 'mode': 'rw'}}
            container = client.containers.run(imageName, ['/bin/bash', '-c', command], tty=True, remove=not debug, privileged=True, name=containerName, 
                volumes=volumes, detach=True)
        except Exception as e:
            # free allocated CPU and virtioID
            cpuAllo.freeSource(startCPU, vnfi.maxCPUNum)
            vioAllo.freeSource(vioStart, 2)
            raise e
        return container.id, startCPU, vioStart

    def _addLB(self, vnfi, client, vioAllo, cpuAllo, debug=vcConfig.DEBUG):
        LB = vnfi.config['LB']
        startCPU = cpuAllo.allocateSource(vnfi.maxCPUNum)
        endCPU = startCPU + vnfi.maxCPUNum - 1
        vioStart = vioAllo.allocateSource(2)
        _vdev0 = self._sibm.getVdev(vnfi.VNFIID, 0).split(',')
        _vdev1 = self._sibm.getVdev(vnfi.VNFIID, 1).split(',')
        vdev0 = '%s,path=%s' % ('net_virtio_user%d' % vioStart, _vdev0[1][6:])
        vdev1 = '%s,path=%s' % ('net_virtio_user%d' % (vioStart + 1) , _vdev1[1][6:])
        imageName = vcConfig.LB_IMAGE_CLICK
        appName = vcConfig.LB_APP_CLICK
        containerName = 'vnf-%s' % vnfi.VNFIID 
        try:
            declLine = 'VIP %s' % LB.vip
            for dst in LB.dst:
                declLine = declLine + ', DST %s' % dst
            declLine = 'lb :: IPLoadBalancer(%s)' % declLine
            command = 'sed -i \"1i\\%s\" %s' % (declLine, vcConfig.LB_APP_CLICK)
            command = command + ' && ./fastclick/bin/click --dpdk -l %d-%d -n 1 -m %d --no-pci --vdev=%s --vdev=%s -- %s' % (startCPU, endCPU, vnfi.maxMem, vdev0, vdev1, appName)
            #logging.info(command)
            volumes = {'/mnt/huge_1GB': {'bind': '/dev/hugepages', 'mode': 'rw'}, '/tmp/': {'bind': '/tmp/', 'mode': 'rw'}}
            container = client.containers.run(imageName, ['/bin/bash', '-c', command], tty=True, remove=not debug, privileged=True, name=containerName, 
                volumes=volumes, detach=True)
        except Exception as e:
            # free allocated CPU and virtioID
            cpuAllo.freeSource(startCPU, vnfi.maxCPUNum)
            vioAllo.freeSource(vioStart, 2)
            raise e
        return container.id, startCPU, vioStart