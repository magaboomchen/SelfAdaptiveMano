#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging
import docker
import paramiko

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
        cpuAllo.freeSource(vnfiDS.cpuStart, vnfiDS.vnfi.maxCPUNum)
        server = vnfiDS.vnfi.node
        ''' kill container '''        
        docker_url = 'tcp://%s:%d' % (server.getControlNICIP(), self._dockerPort)
        client = docker.DockerClient(base_url=docker_url, timeout=5)
        containerID = vnfiDS.containerID
        try:
            container = client.containers.get(containerID)
            container.kill()
        except:
            pass
        ''' remove rule file '''
        if vnfiDS.vnfi.VNFType == VNF_TYPE_FW:
            sshClient = paramiko.SSHClient()
            sshClient.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            # hardcode
            sshClient.connect(hostname=server.getControlNICIP(), port=22, username='t1', password='t1@netlab325')
            
            sftp = sshClient.open_sftp()
            sftp.chdir(vcConfig.RULE_PATH)
            ruleDir = '%s/%s' % (sftp.getcwd(), vnfiDS.vnfi.VNFIID)
            rulePath = '%s/statelessFW' % ruleDir
            sftp.remove(rulePath)
            sftp.rmdir(ruleDir)
            sftp.close()
            sshClient.close()