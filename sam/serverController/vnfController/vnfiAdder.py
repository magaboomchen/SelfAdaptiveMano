#!/usr/bin/python
# -*- coding: UTF-8 -*-

import docker

from sam.base.acl import ACLTable, ACLTuple
from sam.base.rateLimiter import RateLimiterConfig
from sam.base.routingMorphic import IPV4_ROUTE_PROTOCOL, IPV6_ROUTE_PROTOCOL, \
                                    ROCEV1_ROUTE_PROTOCOL, SRV6_ROUTE_PROTOCOL
from sam.base.vnf import VNF_TYPE_FORWARD, VNF_TYPE_FW, VNF_TYPE_FORWARD, \
        VNF_TYPE_FW, VNF_TYPE_MONITOR, VNF_TYPE_LB, VNF_TYPE_NAT, \
        VNF_TYPE_RATELIMITER, VNF_TYPE_VPN
from sam.serverController.sffController.sfcConfig import CHAIN_TYPE_NSHOVERETH, \
                                            CHAIN_TYPE_UFRR, DEFAULT_CHAIN_TYPE
from sam.serverController.sffController.sibMaintainer import SIBMaintainer
from sam.serverController.vnfController.vcConfig import vcConfig


class VNFIAdder(object):
    def __init__(self, dockerPort, logger):
        self._sibm = SIBMaintainer()
        self._dockerPort = dockerPort
        self.logger = logger

    def addVNFI(self, vnfi, vioAllo, cpuAllo, socketPortAllo):  
        server = vnfi.node
        docker_url = 'tcp://%s:%d' % (server.getControlNICIP(), self._dockerPort)
        self.logger.info("docker_url is {0}".format(docker_url))
        dockerClient = docker.DockerClient(base_url=docker_url, timeout=5)
        self.apiClient = docker.APIClient(base_url=docker_url)

        # inf = dockerClient.info()
        # self.logger.info("dockerClient inf {0}".format(inf))

        vnfiType = vnfi.vnfType
        if vnfiType == VNF_TYPE_FORWARD:  # add testpmd
            return self._addFWD(vnfi, dockerClient, vioAllo, cpuAllo, socketPortAllo)
        elif vnfiType == VNF_TYPE_FW:
            return self._addFW(vnfi, dockerClient, vioAllo, cpuAllo, socketPortAllo)
        elif vnfiType == VNF_TYPE_LB:
            return self._addLB(vnfi, dockerClient, vioAllo, cpuAllo, socketPortAllo)
        elif vnfiType == VNF_TYPE_MONITOR:
            return self._addMON(vnfi, dockerClient, vioAllo, cpuAllo, socketPortAllo)
        elif vnfiType == VNF_TYPE_NAT:
            return self._addNAT(vnfi, dockerClient, vioAllo, cpuAllo, socketPortAllo)
        elif vnfiType == VNF_TYPE_VPN:
            return self._addVPN(vnfi, dockerClient, vioAllo, cpuAllo, socketPortAllo)
        elif vnfiType == VNF_TYPE_RATELIMITER:
            return self._addRateLimiter(vnfi, dockerClient, vioAllo, cpuAllo, socketPortAllo)
        else:
            dockerClient.close()
            raise ValueError("Unknown vnf type {0}".format(vnfiType))

    def _addFWD(self, vnfi, dockerClient, vioAllo, cpuAllo, socketPortAllo, useFastClick=vcConfig.DEFAULT_FASTCLICK, debug=vcConfig.DEBUG):
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
            command = command + " && %s --dpdk -l %s -n 1 --socket-mem %s --file-prefix %s --no-pci --vdev=%s --vdev=%s  -- %s" % (vcConfig.CLICK_PATH, cpuStr, socketMem, filePrefix, vdev0, vdev1, appName)
        containerName = 'vnf-%s' % vnfi.vnfiID
        try:
            #print(command)
            self.logger.info("command is {0}".format(command))
            volumes = {'/mnt/huge_1GB': {'bind': '/dev/hugepages', 'mode': 'rw'}, '/tmp/': {'bind': '/tmp/', 'mode': 'rw'}}
            ports = {'%d/tcp' % vcConfig.CLICK_CONTROLL_SOCKET_PORT: None}
            container = dockerClient.containers.run(imageName, ['/bin/bash', '-c', command], tty=True, remove=not debug, privileged=True, name=containerName, 
                volumes=volumes, detach=True, ports=ports)
            self.logger.info("container's logs: {0}".format(container.logs()))
        except Exception as e:
            # free allocated CPU and virtioID
            cpuAllo.freeCPU(cpus)
            vioAllo.freeSource(vioStart, 2)
            raise e

        controlSocketPort = self._getContainerHostPort(container)
        socketPortAllo.allocateSpecificSocketPort(controlSocketPort)

        return container.id, cpus, vioStart, controlSocketPort

    def _addFW(self, vnfi, dockerClient, vioAllo, cpuAllo, socketPortAllo, debug=vcConfig.DEBUG):
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
        # appName = vcConfig.FW_APP_CLICK
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
            clickConfFilePath = vcConfig.FW_APP_CLICK + "_" + containerName + ".click"
            appName = clickConfFilePath
            command = ' cp %s %s' %(vcConfig.FW_APP_CLICK, clickConfFilePath)
            if not vcConfig.USING_PRECONFIG:
                command = command + ' && sed -i \"1i\\%s\" %s' % (dpdkInfo, clickConfFilePath)
                command = command + ' && mkdir -p %s' % vcConfig.FW_RULE_DIR
                if DEFAULT_CHAIN_TYPE == CHAIN_TYPE_UFRR:
                    if type(vnfi.config) == ACLTable:
                        aclTable = vnfi.config  # type: ACLTable
                        ipv4ACLRulesList = aclTable.getRulesList(IPV4_ROUTE_PROTOCOL)    # type: list(ACLTuple)
                        for rule in ipv4ACLRulesList:
                            command = command + ' && echo \"%s\" >> %s' % (rule.genFWLine(), vcConfig.FW_IPV4_RULE_PATH)
                elif DEFAULT_CHAIN_TYPE == CHAIN_TYPE_NSHOVERETH:
                    if type(vnfi.config) == ACLTable:
                        aclTable = vnfi.config  # type: ACLTable
                        if aclTable.getRulesNum(IPV4_ROUTE_PROTOCOL) != 0:
                            ipv4ACLRulesList = aclTable.getRulesList(IPV4_ROUTE_PROTOCOL)
                            newIPV4FWRulesFileName = "statelessIPV4FWRules_" +  containerName
                            newIPV4FWRulesPath = vcConfig.FW_RULE_DIR + '/' + newIPV4FWRulesFileName
                            command = command + ' && sed -i \'s/statelessIPV4FWRules/%s/\' %s' % (newIPV4FWRulesFileName, clickConfFilePath)
                            for rule in ipv4ACLRulesList:
                                command = command + ' && echo \"%s\" >> %s' % (rule.genFWLine(), newIPV4FWRulesPath)
                        if aclTable.getRulesNum(IPV6_ROUTE_PROTOCOL) != 0:
                            ipv6ACLRulesList = aclTable.getRulesList(IPV6_ROUTE_PROTOCOL)
                            newIPV6FWRulesFileName = "statelessIPV6FWRules_" +  containerName
                            newIPV6FWRulesPath = vcConfig.FW_RULE_DIR + '/' + newIPV6FWRulesFileName
                            command = command + ' && sed -i \'s/statelessIPV6FWRules/%s/\' %s' % (newIPV6FWRulesFileName, clickConfFilePath)
                            for rule in ipv6ACLRulesList:
                                command = command + ' && echo \"%s\" >> %s' % (rule.gen128BitsDstIdentifierFWLine(), newIPV6FWRulesPath)
                        if aclTable.getRulesNum(SRV6_ROUTE_PROTOCOL) != 0:
                            ipv6ACLRulesList = aclTable.getRulesList(SRV6_ROUTE_PROTOCOL)
                            newIPV6FWRulesFileName = "statelessIPV6FWRules_" +  containerName
                            newIPV6FWRulesPath = vcConfig.FW_RULE_DIR + '/' + newIPV6FWRulesFileName
                            command = command + ' && sed -i \'s/statelessIPV6FWRules/%s/\' %s' % (newIPV6FWRulesFileName, clickConfFilePath)
                            for rule in ipv6ACLRulesList:
                                command = command + ' && echo \"%s\" >> %s' % (rule.gen128BitsDstIdentifierFWLine(), newIPV6FWRulesPath)
                        if aclTable.getRulesNum(ROCEV1_ROUTE_PROTOCOL) != 0:
                            rocev1ACLRulesList = aclTable.getRulesList(ROCEV1_ROUTE_PROTOCOL)
                            newROCEV1FWRulesFileName = "statelessROCEV1FWRules_" +  containerName
                            newROCEV1FWRulesPath = vcConfig.FW_RULE_DIR + '/' + newROCEV1FWRulesFileName
                            command = command + ' && sed -i \'s/statelessROCEV1FWRules/%s/\' %s' % (newROCEV1FWRulesFileName, clickConfFilePath)
                            for rule in rocev1ACLRulesList:
                                command = command + ' && echo \"%s\" >> %s' % (rule.gen128BitsDstIdentifierFWLine(), newROCEV1FWRulesPath)
                else:
                    raise ValueError("Unknown chain type {0}".format(DEFAULT_CHAIN_TYPE))
                command = command + ' && %s --dpdk -l %s -n 1 --socket-mem %s --file-prefix %s --no-pci --vdev=%s --vdev=%s -- %s' % (vcConfig.CLICK_PATH, cpuStr, socketMem, filePrefix, vdev0, vdev1, appName)
                self.logger.info(command)
                volumes = {'/mnt/huge_1GB': {'bind': '/dev/hugepages', 'mode': 'rw'}, '/tmp/': {'bind': '/tmp/', 'mode': 'rw'}}
                #ulimit = docker.types.Ulimit(name='stack', soft=268435456, hard=268435456)
            else:
                command = command + ' && sed -i \"1i\\%s\" %s' % (dpdkInfo, clickConfFilePath)
                command = command + ' && %s --dpdk -l %s -n 1 --socket-mem %s --file-prefix %s --no-pci --vdev=%s --vdev=%s -- %s' % (vcConfig.CLICK_PATH, cpuStr, socketMem, filePrefix, vdev0, vdev1, appName)
                if vcConfig.DEBUG:
                    volumes = {'/mnt/huge_1GB': {'bind': '/dev/hugepages', 'mode': 'rw'}, '/tmp/': {'bind': '/tmp/', 'mode': 'rw'}, vcConfig.PRECONFIG_PATH: {'bind': vcConfig.FW_RULE_DIR, 'mode': 'rw'}}
                else:
                    volumes = {'/mnt/huge_1GB': {'bind': '/dev/hugepages', 'mode': 'rw'}, '/tmp/': {'bind': '/tmp/', 'mode': 'rw'}}
            ports = {'%d/tcp' % vcConfig.CLICK_CONTROLL_SOCKET_PORT: None}
            container = dockerClient.containers.run(imageName, ['/bin/bash', '-c', command], tty=True, remove=not debug, privileged=True, name=containerName, 
                volumes=volumes, detach=True, ports=ports) #, ulimits=[ulimit])
            
            # self.logger.info("container status {0}".format(container.status))

        except Exception as e:
            # free allocated CPU and virtioID
            cpuAllo.freeCPU(cpus)
            vioAllo.freeSource(vioStart, 2)
            raise e

        controlSocketPort = self._getContainerHostPort(container)
        socketPortAllo.allocateSpecificSocketPort(controlSocketPort)

        return container.id, cpus, vioStart, controlSocketPort

    def _addRateLimiter(self, vnfi, dockerClient, vioAllo, cpuAllo, socketPortAllo, debug=vcConfig.DEBUG):   
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
        imageName = vcConfig.RATELIMITER_IMAGE_CLICK
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
            clickConfFilePath = vcConfig.RATELIMITER_APP_CLICK + "_" + containerName + ".click"
            appName = clickConfFilePath
            command = ' cp %s %s' %(vcConfig.RATELIMITER_APP_CLICK, clickConfFilePath)
            if type(vnfi.config) == RateLimiterConfig:
                maxRate = vnfi.config.maxMbps
                command = command + ' && sed -i \'s/2000Bps/%sBps/\' %s' % (maxRate*1000.0, clickConfFilePath)
            command = command + ' && sed -i \"1i\\%s\" %s' % (dpdkInfo, clickConfFilePath)
            command = command + ' && %s --dpdk -l %s -n 1 --socket-mem %s --file-prefix %s --no-pci --vdev=%s --vdev=%s -- %s' % (vcConfig.CLICK_PATH, cpuStr, socketMem, filePrefix, vdev0, vdev1, appName)
            volumes = {'/mnt/huge_1GB': {'bind': '/dev/hugepages', 'mode': 'rw'}, '/tmp/': {'bind': '/tmp/', 'mode': 'rw'}}
            ports = {'%d/tcp' % vcConfig.CLICK_CONTROLL_SOCKET_PORT: None}
            container = dockerClient.containers.run(imageName, ['/bin/bash', '-c', command], tty=True, remove=not debug, privileged=True, name=containerName, 
                volumes=volumes, detach=True, ports=ports) #, ulimits=[ulimit])

        except Exception as e:
            # free allocated CPU and virtioID
            cpuAllo.freeCPU(cpus)
            vioAllo.freeSource(vioStart, 2)
            raise e

        controlSocketPort = self._getContainerHostPort(container)
        socketPortAllo.allocateSpecificSocketPort(controlSocketPort)

        return container.id, cpus, vioStart, controlSocketPort

    def _addLB(self, vnfi, dockerClient, vioAllo, cpuAllo, socketPortAllo, debug=vcConfig.DEBUG):
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
            command = command + ' && %s --dpdk -l %s -n 1 --socket-mem %s --file-prefix %s --no-pci --vdev=%s --vdev=%s -- %s' % (vcConfig.CLICK_PATH, cpuStr, socketMem, filePrefix, vdev0, vdev1, appName)
            #print(command)
            volumes = {'/mnt/huge_1GB': {'bind': '/dev/hugepages', 'mode': 'rw'}, '/tmp/': {'bind': '/tmp/', 'mode': 'rw'}}
            ports = {'%d/tcp' % vcConfig.CLICK_CONTROLL_SOCKET_PORT: None}
            container = dockerClient.containers.run(imageName, ['/bin/bash', '-c', command], tty=True, remove=not debug, privileged=True, name=containerName, 
                volumes=volumes, detach=True, ports=ports)
        except Exception as e:
            # free allocated CPU and virtioID
            cpuAllo.freeCPU(cpus)
            vioAllo.freeSource(vioStart, 2)
            raise e

        controlSocketPort = self._getContainerHostPort(container)
        socketPortAllo.allocateSpecificSocketPort(controlSocketPort)

        return container.id, cpus, vioStart, controlSocketPort

    def _addMON(self, vnfi, dockerClient, vioAllo, cpuAllo, socketPortAllo, debug=vcConfig.DEBUG):
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
        clickConfFilePath = vcConfig.MON_APP_CLICK + "_" + containerName + ".click"
        appName = clickConfFilePath
        command = ' cp %s %s' %(vcConfig.MON_APP_CLICK, clickConfFilePath)
        command = command + '&& sed -i \"1i\\%s\" %s' % (dpdkInfo, vcConfig.MON_APP_CLICK)
        # command = command + ' && sed -i \'s/7777/%s/\' %s' % (controlSocketPort, clickConfFilePath)
        command = command + " && %s --dpdk -l %s -n 1 --socket-mem %s --file-prefix %s --no-pci --vdev=%s --vdev=%s -- %s" % (vcConfig.CLICK_PATH, cpuStr, socketMem, filePrefix, vdev0, vdev1, appName)
        volumes = {'/mnt/huge_1GB': {'bind': '/dev/hugepages', 'mode': 'rw'}, '/tmp/': {'bind': '/tmp/', 'mode': 'rw'}}
        ports = {'%d/tcp' % vcConfig.CLICK_CONTROLL_SOCKET_PORT: None}
        # ports = {'%d/tcp' % vcConfig.CLICK_CONTROLL_SOCKET_PORT: controlSocketPort}
        try:
            container = dockerClient.containers.run(imageName, ['/bin/bash', '-c', command], tty=True, remove=not debug, privileged=True, name=containerName, 
                volumes=volumes, detach=True, ports=ports)
        except Exception as e:
            # free allocated CPU and virtioID
            cpuAllo.freeCPU(cpus)
            vioAllo.freeSource(vioStart, 2)
            raise e
        
        controlSocketPort = self._getContainerHostPort(container)
        socketPortAllo.allocateSpecificSocketPort(controlSocketPort)

        return container.id, cpus, vioStart, controlSocketPort
        
    def _addNAT(self, vnfi, dockerClient, vioAllo, cpuAllo, socketPortAllo, debug=vcConfig.DEBUG):
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
            command = command + ' && %s --dpdk -l %s -n 1 --socket-mem %s --file-prefix %s --no-pci --vdev=%s --vdev=%s -- %s' % (vcConfig.CLICK_PATH, cpuStr, socketMem, filePrefix, vdev0, vdev1, appName)
            self.logger.info(command)
            volumes = {'/mnt/huge_1GB': {'bind': '/dev/hugepages', 'mode': 'rw'}, '/tmp/': {'bind': '/tmp/', 'mode': 'rw'}}
            ports = {'%d/tcp' % vcConfig.CLICK_CONTROLL_SOCKET_PORT: None}
            container = dockerClient.containers.run(imageName, ['/bin/bash', '-c', command], tty=True, remove=not debug, privileged=True, name=containerName, 
                volumes=volumes, detach=True, ports=ports)
        except Exception as e:
            # free allocated CPU and virtioID
            cpuAllo.freeCPU(cpus)
            vioAllo.freeSource(vioStart, 2)
            raise e
        
        controlSocketPort = self._getContainerHostPort(container)
        socketPortAllo.allocateSpecificSocketPort(controlSocketPort)

        return container.id, cpus, vioStart, controlSocketPort

    def _addVPN(self, vnfi, dockerClient, vioAllo, cpuAllo, socketPortAllo, debug=vcConfig.DEBUG):
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
        # command = "%s --dpdk -l %d-%d -n 1 -m %d --no-pci --vdev=%s --vdev=%s -- %s" % (vcConfig.CLICK_PATH, startCPU, endCPU, vnfi.maxMem, vdev0, vdev1, appName)
        declLine = "%s 0 234 \\\\\\\\<%s> \\\\\\\\<%s> 300 64," % (VPN.tunnelSrcIP, VPN.encryptKey, VPN.authKey)
        command = "sed -i \"3i %s\" %s" % (declLine, vcConfig.VPN_APP_CLICK)
        declLine = "0.0.0.0/0 %s 1 234 \\\\\\\\<%s> \\\\\\\\<%s> 300 64" % (VPN.tunnelDstIP, VPN.encryptKey, VPN.authKey)
        command = command + " && sed -i \"4i %s\" %s" % (declLine, vcConfig.VPN_APP_CLICK)
        # command = command + " && cat ./click-conf/vpn.click "
        command = command + ' && sed -i \"1i\\%s\" %s' % (dpdkInfo, vcConfig.VPN_APP_CLICK)
        command = command + ' && %s --dpdk -l %s -n 1 --socket-mem %s --file-prefix %s --no-pci --vdev=%s --vdev=%s -- %s' % (vcConfig.CLICK_PATH, cpuStr, socketMem, filePrefix, vdev0, vdev1, appName)
        containerName = 'vnf-%s' % vnfi.vnfiID
        try:
            volumes = {'/mnt/huge_1GB': {'bind': '/dev/hugepages', 'mode': 'rw'}, '/tmp/': {'bind': '/tmp/', 'mode': 'rw'}}
            ports = {'%d/tcp' % vcConfig.CLICK_CONTROLL_SOCKET_PORT: None}
            container = dockerClient.containers.run(imageName, ['/bin/bash', '-c', command], tty=True, remove=not debug, privileged=True, name=containerName, 
                volumes=volumes, detach=True, ports=ports)
            self.logger.info(container.logs())
        except Exception as e:
            # free allocated CPU and virtioID
            cpuAllo.freeCPU(cpus)
            vioAllo.freeSource(vioStart, 2)
            raise e

        controlSocketPort = self._getContainerHostPort(container)
        socketPortAllo.allocateSpecificSocketPort(controlSocketPort)

        return container.id, cpus, vioStart, controlSocketPort

    def _getContainerHostPort(self, container):
        # to get the host port of this container
        container.reload()
        if len(container.ports) != 0:
            for key in container.ports:
                controlSocketPort = int(container.ports[key][0]['HostPort'])
                self.logger.debug("controlSocketPort is {0}".format(controlSocketPort))
                return controlSocketPort
        else:
            raise ValueError("Can't get controlSocketPort!")

        # self.logger.info("container.id is {0}".format(container.id))
        # port_data = self.apiClient.inspect_container(container.id)['NetworkSettings']['Ports']
        # self.logger.info("port_data is {0}".format(port_data))
        # return port_data[0]['HostPort']
