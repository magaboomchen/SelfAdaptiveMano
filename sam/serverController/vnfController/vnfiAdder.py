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

        vnfiType = vnfi.vnfType
        if vnfiType == VNF_TYPE_FORWARD:  # add testpmd
            return self._addFWD(vnfi, client, vioAllo, cpuAllo)
        elif vnfiType == VNF_TYPE_FW:
            return self._addFW(vnfi, client, vioAllo, cpuAllo)
        elif vnfiType == VNF_TYPE_LB:
            return self._addLB(vnfi, client, vioAllo, cpuAllo)
        elif vnfiType == VNF_TYPE_MONITOR:
            return self._addMON(vnfi, client, vioAllo, cpuAllo)
        elif vnfiType == VNF_TYPE_NAT:
            return self._addNAT(vnfi, client, vioAllo, cpuAllo)
        elif vnfiType == VNF_TYPE_VPN:
            return self._addVPN(vnfi, client, vioAllo, cpuAllo)

    def _addFWD(self, vnfi, client, vioAllo, cpuAllo, useFastClick=vcConfig.DEFAULT_FASTCLICK, debug=vcConfig.DEBUG):
        cpus = cpuAllo.allocateCPU(vnfi.maxCPUNum)
        cpuStr = ''
        for each in cpus:
            for cpu in each:
                cpuStr = cpuStr + '%d,' % cpu
        cpuStr = cpuStr[:-1]
        
        vioStart = vioAllo.allocateSource(2)
        _vdev0 = self._sibm.getVdev(vnfi.vnfiID, 0).split(',')
        _vdev1 = self._sibm.getVdev(vnfi.vnfiID, 1).split(',')
        vdev0 = '%s,path=%s' % ('net_virtio_user%d' % vioStart, _vdev0[1][6:])
        vdev1 = '%s,path=%s' % ('net_virtio_user%d' % (vioStart + 1) , _vdev1[1][6:])
        if not useFastClick:
            imageName = vcConfig.FWD_IMAGE_DPDK
            appName = vcConfig.FWD_APP_DPDK
            command = "%s -l %s -n 1 -m %d --no-pci --vdev=%s --vdev=%s " % (appName, cpuStr, vnfi.maxMem, vdev0, vdev1) +\
                  '--file-prefix=virtio --log-level=8 -- --txqflags=0xf00 --disable-hw-vlan ' +\
                  '--forward-mode=io --port-topology=chained --total-num-mbufs=2048 -a' 
        else:
            imageName = vcConfig.FWD_IMAGE_CLICK
            appName = vcConfig.FWD_APP_CLICK

            filePrefix = "fwd-%d" % (vioStart / 2)

            dpdkInfo = 'DPDKInfo('
            socketMem = '' 
            for each in cpus:
                if len(each) != 0:
                    dpdkInfo = dpdkInfo + 'NB_SOCKET_MBUF %d, ' % vcConfig.DPDKINFO_BUF
                    socketMem = socketMem + '%d,' % vnfi.maxMem
                else:
                    dpdkInfo = dpdkInfo + 'NB_SOCKET_MBUF 0, '
                    socketMem = socketMem + '%d,' % 0
            dpdkInfo = dpdkInfo[:-2] + ')'
            socketMem = socketMem[:-1]

            command = 'sed -i \"1i\\%s\" %s' % (dpdkInfo, vcConfig.FWD_APP_CLICK)
            command = command + " && ./fastclick/bin/click --dpdk -l %s -n 1 --socket-mem %s --file-prefix %s --no-pci --vdev=%s --vdev=%s  -- %s" % (cpuStr, socketMem, filePrefix, vdev0, vdev1, appName)
        containerName = 'vnf-%s' % vnfi.vnfiID
        try:
            #print(command)
            volumes = {'/mnt/huge_1GB': {'bind': '/dev/hugepages', 'mode': 'rw'}, '/tmp/': {'bind': '/tmp/', 'mode': 'rw'}}
            container = client.containers.run(imageName, ['/bin/bash', '-c', command], tty=True, remove=not debug, privileged=True, name=containerName, 
                volumes=volumes, detach=True, ports = {'%d/tcp' % vcConfig.MON_TCP_PORT: None})
            #logging.info(container.logs())
        except Exception as e:
            # free allocated CPU and virtioID
            cpuAllo.freeCPU(cpus)
            vioAllo.freeSource(vioStart, 2)
            raise e
        return container.id, cpus, vioStart

    def _addFW(self, vnfi, client, vioAllo, cpuAllo, debug=vcConfig.DEBUG):
        ACL = vnfi.config['ACL']        
        cpus = cpuAllo.allocateCPU(vnfi.maxCPUNum)
        cpuStr = ''
        for each in cpus:
            for cpu in each:
                cpuStr = cpuStr + '%d,' % cpu
        cpuStr = cpuStr[:-1]
        vioStart = vioAllo.allocateSource(2)
        _vdev0 = self._sibm.getVdev(vnfi.vnfiID, 0).split(',')
        _vdev1 = self._sibm.getVdev(vnfi.vnfiID, 1).split(',')
        vdev0 = '%s,path=%s' % ('net_virtio_user%d' % vioStart, _vdev0[1][6:])
        vdev1 = '%s,path=%s' % ('net_virtio_user%d' % (vioStart + 1) , _vdev1[1][6:])
        imageName = vcConfig.FW_IMAGE_CLICK
        appName = vcConfig.FW_APP_CLICK
        containerName = 'vnf-%s' % vnfi.vnfiID 
        filePrefix = 'fw-%d' % (vioStart / 2)
        dpdkInfo = 'DPDKInfo('
        socketMem = '' 
        for each in cpus:
            if len(each) != 0:
                dpdkInfo = dpdkInfo + 'NB_SOCKET_MBUF %d, ' % vcConfig.DPDKINFO_BUF
                socketMem = socketMem + '%d,' % vnfi.maxMem
            else:
                dpdkInfo = dpdkInfo + 'NB_SOCKET_MBUF 0, '
                socketMem = socketMem + '%d,' % 0
        dpdkInfo = dpdkInfo[:-2] + ')'
        socketMem = socketMem[:-1]
        try:
            if not vcConfig.USING_PRECONFIG:
                command = 'sed -i \"1i\\%s\" %s' % (dpdkInfo, vcConfig.FW_APP_CLICK)
                command = command + ' && mkdir %s' % vcConfig.FW_RULE_DIR
                for rule in ACL:
                    command = command + ' && echo \"%s\" >> %s' % (rule.genFWLine(), vcConfig.FW_RULE_PATH)
                command = command + ' && ./fastclick/bin/click --dpdk -l %s -n 1 --socket-mem %s --file-prefix %s --no-pci --vdev=%s --vdev=%s -- %s' % (cpuStr, socketMem, filePrefix, vdev0, vdev1, appName)
                #logging.info(command)
                volumes = {'/mnt/huge_1GB': {'bind': '/dev/hugepages', 'mode': 'rw'}, '/tmp/': {'bind': '/tmp/', 'mode': 'rw'}}
                #ulimit = docker.types.Ulimit(name='stack', soft=268435456, hard=268435456)
            else:
                command = 'sed -i \"1i\\%s\" %s' % (dpdkInfo, vcConfig.FW_APP_CLICK)
                command = command + ' && ./fastclick/bin/click --dpdk -l %s -n 1 --socket-mem %s --file-prefix %s --no-pci --vdev=%s --vdev=%s -- %s' % (cpuStr, socketMem, filePrefix, vdev0, vdev1, appName)
                volumes = {'/mnt/huge_1GB': {'bind': '/dev/hugepages', 'mode': 'rw'}, '/tmp/': {'bind': '/tmp/', 'mode': 'rw'}, vcConfig.PRECONFIG_PATH: {'bind': vcConfig.FW_RULE_DIR, 'mode': 'rw'}}
            container = client.containers.run(imageName, ['/bin/bash', '-c', command], tty=True, remove=not debug, privileged=True, name=containerName, 
                volumes=volumes, detach=True) #, ulimits=[ulimit])

        except Exception as e:
            # free allocated CPU and virtioID
            cpuAllo.freeCPU(cpus)
            vioAllo.freeSource(vioStart, 2)
            raise e
        return container.id, cpus, vioStart

    def _addLB(self, vnfi, client, vioAllo, cpuAllo, debug=vcConfig.DEBUG):
        LB = vnfi.config['LB']
        cpus = cpuAllo.allocateCPU(vnfi.maxCPUNum)
        cpuStr = ''
        for each in cpus:
            for cpu in each:
                cpuStr = cpuStr + '%d,' % cpu
        cpuStr = cpuStr[:-1]
        vioStart = vioAllo.allocateSource(2)
        _vdev0 = self._sibm.getVdev(vnfi.vnfiID, 0).split(',')
        _vdev1 = self._sibm.getVdev(vnfi.vnfiID, 1).split(',')
        vdev0 = '%s,path=%s' % ('net_virtio_user%d' % vioStart, _vdev0[1][6:])
        vdev1 = '%s,path=%s' % ('net_virtio_user%d' % (vioStart + 1) , _vdev1[1][6:])
        imageName = vcConfig.LB_IMAGE_CLICK
        appName = vcConfig.LB_APP_CLICK
        containerName = 'vnf-%s' % vnfi.vnfiID 
        filePrefix = 'LB-%d' % (vioStart / 2)
        dpdkInfo = 'DPDKInfo('
        socketMem = '' 
        for each in cpus:
            if len(each) != 0:
                dpdkInfo = dpdkInfo + 'NB_SOCKET_MBUF %d, ' % vcConfig.DPDKINFO_BUF
                socketMem = socketMem + '%d,' % vnfi.maxMem
            else:
                dpdkInfo = dpdkInfo + 'NB_SOCKET_MBUF 0, '
                socketMem = socketMem + '%d,' % 0
        dpdkInfo = dpdkInfo[:-2] + ')'
        socketMem = socketMem[:-1]
        try:
            declLine = 'VIP %s' % LB.vip
            for dst in LB.dst:
                declLine = declLine + ', DST %s' % dst
            declLine = 'lb :: IPLoadBalancer(%s)' % declLine
            command = 'sed -i \"1i\\%s\" %s' % (declLine, vcConfig.LB_APP_CLICK)
            command = command + ' && sed -i \"1i\\%s\" %s' % (dpdkInfo, vcConfig.LB_APP_CLICK)
            command = command + ' && ./fastclick/bin/click --dpdk -l %s -n 1 --socket-mem %s --file-prefix %s --no-pci --vdev=%s --vdev=%s -- %s' % (cpuStr, socketMem, filePrefix, vdev0, vdev1, appName)
            #print(command)
            volumes = {'/mnt/huge_1GB': {'bind': '/dev/hugepages', 'mode': 'rw'}, '/tmp/': {'bind': '/tmp/', 'mode': 'rw'}}
            container = client.containers.run(imageName, ['/bin/bash', '-c', command], tty=True, remove=not debug, privileged=True, name=containerName, 
                volumes=volumes, detach=True)
        except Exception as e:
            # free allocated CPU and virtioID
            cpuAllo.freeCPU(cpus)
            vioAllo.freeSource(vioStart, 2)
            raise e
        return container.id, cpus, vioStart

    def _addMON(self, vnfi, client, vioAllo, cpuAllo, debug=vcConfig.DEBUG):
        cpus = cpuAllo.allocateCPU(vnfi.maxCPUNum)
        cpuStr = ''
        for each in cpus:
            for cpu in each:
                cpuStr = cpuStr + '%d,' % cpu
        cpuStr = cpuStr[:-1]
        vioStart = vioAllo.allocateSource(2)
        _vdev0 = self._sibm.getVdev(vnfi.vnfiID, 0).split(',')
        _vdev1 = self._sibm.getVdev(vnfi.vnfiID, 1).split(',')
        vdev0 = '%s,path=%s' % ('net_virtio_user%d' % vioStart, _vdev0[1][6:])
        vdev1 = '%s,path=%s' % ('net_virtio_user%d' % (vioStart + 1) , _vdev1[1][6:])
        imageName = vcConfig.MON_IMAGE_CLICK
        appName = vcConfig.MON_APP_CLICK
        containerName = 'vnf-%s' % vnfi.vnfiID 
        filePrefix = 'MON-%d' % (vioStart / 2)
        dpdkInfo = 'DPDKInfo('
        socketMem = '' 
        for each in cpus:
            if len(each) != 0:
                dpdkInfo = dpdkInfo + 'NB_SOCKET_MBUF %d, ' % vcConfig.DPDKINFO_BUF
                socketMem = socketMem + '%d,' % vnfi.maxMem
            else:
                dpdkInfo = dpdkInfo + 'NB_SOCKET_MBUF 0, '
                socketMem = socketMem + '%d,' % 0
        dpdkInfo = dpdkInfo[:-2] + ')'
        socketMem = socketMem[:-1]
        command = 'sed -i \"1i\\%s\" %s' % (dpdkInfo, vcConfig.MON_APP_CLICK)
        command = command + " && ./fastclick/bin/click --dpdk -l %s -n 1 --socket-mem %s --file-prefix %s --no-pci --vdev=%s --vdev=%s -- %s" % (cpuStr, socketMem, filePrefix, vdev0, vdev1, appName)
        volumes = {'/mnt/huge_1GB': {'bind': '/dev/hugepages', 'mode': 'rw'}, '/tmp/': {'bind': '/tmp/', 'mode': 'rw'}}
        ports = {'%d/tcp' % vcConfig.MON_TCP_PORT: None}
        try:
            container = client.containers.run(imageName, ['/bin/bash', '-c', command], tty=True, remove=not debug, privileged=True, name=containerName, 
                volumes=volumes, detach=True, ports=ports)
        except Exception as e:
            # free allocated CPU and virtioID
            cpuAllo.freeCPU(cpus)
            vioAllo.freeSource(vioStart, 2)
            raise e
        
        # to get the host port of this container
        '''
        container.reload()
        for key in container.ports:
            print(int(container.ports[key][0]['HostPort']))
        '''
        return container.id, cpus, vioStart

    def _addNAT(self, vnfi, client, vioAllo, cpuAllo, debug=vcConfig.DEBUG):
        NAT = vnfi.config['NAT']
        cpus = cpuAllo.allocateCPU(1)
        cpuStr = ''
        for each in cpus:
            for cpu in each:
                cpuStr = cpuStr + '%d,' % cpu
        cpuStr = cpuStr[:-1]
        vioStart = vioAllo.allocateSource(2)
        _vdev0 = self._sibm.getVdev(vnfi.vnfiID, 0).split(',')
        _vdev1 = self._sibm.getVdev(vnfi.vnfiID, 1).split(',')
        vdev0 = '%s,path=%s' % ('net_virtio_user%d' % vioStart, _vdev0[1][6:])
        vdev1 = '%s,path=%s' % ('net_virtio_user%d' % (vioStart + 1) , _vdev1[1][6:])
        imageName = vcConfig.NAT_IMAGE_CLICK    
        appName = vcConfig.NAT_APP_CLICK
        containerName = 'vnf-%s' % vnfi.vnfiID 
        filePrefix = 'NAT-%d' % (vioStart / 2)
        dpdkInfo = 'DPDKInfo('
        socketMem = '' 
        for each in cpus:
            if len(each) != 0:
                dpdkInfo = dpdkInfo + 'NB_SOCKET_MBUF %d, ' % vcConfig.DPDKINFO_BUF
                socketMem = socketMem + '%d,' % vnfi.maxMem
            else:
                dpdkInfo = dpdkInfo + 'NB_SOCKET_MBUF 0, '
                socketMem = socketMem + '%d,' % 0
        dpdkInfo = dpdkInfo[:-2] + ')'
        socketMem = socketMem[:-1]
        try:
            declLine = 'nat :: IPRewriterPatterns(NAT %s %d-%d - -)' % (NAT.pubIP, NAT.minPort, NAT.maxPort)
            command = 'sed -i \"1i\\%s\" %s' % (declLine, vcConfig.NAT_APP_CLICK)
            command = command + ' && sed -i \"1i\\%s\" %s' % (dpdkInfo, vcConfig.NAT_APP_CLICK)
            command = command + ' && ./fastclick/bin/click --dpdk -l %s -n 1 --socket-mem %s --file-prefix %s --no-pci --vdev=%s --vdev=%s -- %s' % (cpuStr, socketMem, filePrefix, vdev0, vdev1, appName)
            #logging.info(command)
            volumes = {'/mnt/huge_1GB': {'bind': '/dev/hugepages', 'mode': 'rw'}, '/tmp/': {'bind': '/tmp/', 'mode': 'rw'}}
            container = client.containers.run(imageName, ['/bin/bash', '-c', command], tty=True, remove=not debug, privileged=True, name=containerName, 
                volumes=volumes, detach=True) #, ports=ports)
        except Exception as e:
            # free allocated CPU and virtioID
            cpuAllo.freeCPU(cpus)
            vioAllo.freeSource(vioStart, 2)
            raise e
        return container.id, cpus, vioStart

    def _addVPN(self, vnfi, client, vioAllo, cpuAllo, debug=vcConfig.DEBUG):
        VPN = vnfi.config['VPN']
        cpus = cpuAllo.allocateCPU(vnfi.maxCPUNum)
        cpuStr = ''
        for each in cpus:
            for cpu in each:
                cpuStr = cpuStr + '%d,' % cpu
        cpuStr = cpuStr[:-1]
        vioStart = vioAllo.allocateSource(2)
        _vdev0 = self._sibm.getVdev(vnfi.vnfiID, 0).split(',')
        _vdev1 = self._sibm.getVdev(vnfi.vnfiID, 1).split(',')
        vdev0 = '%s,path=%s' % ('net_virtio_user%d' % vioStart, _vdev0[1][6:])
        vdev1 = '%s,path=%s' % ('net_virtio_user%d' % (vioStart + 1) , _vdev1[1][6:])
        imageName = vcConfig.VPN_IMAGE_CLICK
        appName = vcConfig.VPN_APP_CLICK
        filePrefix = 'VPN-%d' % (vioStart / 2)
        dpdkInfo = 'DPDKInfo('
        socketMem = '' 
        for each in cpus:
            if len(each) != 0:
                dpdkInfo = dpdkInfo + 'NB_SOCKET_MBUF %d, ' % vcConfig.DPDKINFO_BUF
                socketMem = socketMem + '%d,' % vnfi.maxMem
            else:
                dpdkInfo = dpdkInfo + 'NB_SOCKET_MBUF 0, '
                socketMem = socketMem + '%d,' % 0
        dpdkInfo = dpdkInfo[:-2] + ')'
        socketMem = socketMem[:-1]
        # command = "./fastclick/bin/click --dpdk -l %d-%d -n 1 -m %d --no-pci --vdev=%s --vdev=%s -- %s" % (startCPU, endCPU, vnfi.maxMem, vdev0, vdev1, appName)
        declLine = "%s 0 234 \\\\\\\\<%s> \\\\\\\\<%s> 300 64," % (VPN.tunnelSrcIP, VPN.encryptKey, VPN.authKey)
        command = "sed -i \"3i %s\" %s" % (declLine, vcConfig.VPN_APP_CLICK)
        declLine = "0.0.0.0/0 %s 1 234 \\\\\\\\<%s> \\\\\\\\<%s> 300 64" % (VPN.tunnelDstIP, VPN.encryptKey, VPN.authKey)
        command = command + " && sed -i \"4i %s\" %s" % (declLine, vcConfig.VPN_APP_CLICK)
        # command = command + " && cat ./click-conf/vpn.click "
        command = command + ' && sed -i \"1i\\%s\" %s' % (dpdkInfo, vcConfig.VPN_APP_CLICK)
        command = command + ' && ./fastclick/bin/click --dpdk -l %s -n 1 --socket-mem %s --file-prefix %s --no-pci --vdev=%s --vdev=%s -- %s' % (cpuStr, socketMem, filePrefix, vdev0, vdev1, appName)
        containerName = 'vnf-%s' % vnfi.vnfiID
        try:
            volumes = {'/mnt/huge_1GB': {'bind': '/dev/hugepages', 'mode': 'rw'}, '/tmp/': {'bind': '/tmp/', 'mode': 'rw'}}
            container = client.containers.run(imageName, ['/bin/bash', '-c', command], tty=True, remove=not debug, privileged=True, name=containerName, 
                volumes=volumes, detach=True)
            #logging.info(container.logs())
        except Exception as e:
            # free allocated CPU and virtioID
            cpuAllo.freeCPU(cpus)
            vioAllo.freeSource(vioStart, 2)
            raise e
        return container.id, cpus, vioStart
