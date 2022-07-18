#!/usr/bin/python
# -*- coding: UTF-8 -*-

import docker


class VNFIDeleter(object):
    def __init__(self, dockerPort):
        self._dockerPort = dockerPort
    
    def deleteVNFI(self, vnfiDS, vioAllo, cpuAllo, socketPortAllo):
        if vnfiDS.error is not None:  # this vnfi is not sucessfully deployed
            assert vnfiDS.containerID is None
            return
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
        finally:
            vioAllo.freeSource(vnfiDS.vioStart, 2)
            cpuAllo.freeCPU(vnfiDS.cpus)
            if vnfiDS.controlSocketPort != None:
                socketPortAllo.freeSocketPort(vnfiDS.controlSocketPort)