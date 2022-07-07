#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging

import pytest

from sam.base.sshAgent import SSHAgent

MANUAL_TEST = True

logging.basicConfig(level=logging.INFO)

class TestSSHAgentClass(object):
    def setup_method(self, method):
        """ setup any state tied to the execution of the given method in a
        class.  setup_method is invoked for every test method of a class.
        """
        self.sshA = SSHAgent()
        self.sshA.connectSSH("t1", "123", "127.0.0.1", remoteSSHPort=22)

    def teardown_method(self, method):
        """ teardown any state that was previously setup with a setup_method
        call.
        """
        name = "name1"
        command = "sudo -S docker stop "+name
        logging.info(command)
        shellCmdRply = self.sshA.runShellCommandWithSudo(command,1)
        self.sshA.disconnectSSH()

    def test_runShellCommand(self):
        shellCmdRply = self.sshA.runShellCommand("ls")
        stdin = shellCmdRply['stdin']
        stdout = shellCmdRply['stdout']
        stderr = shellCmdRply['stderr']
        logging.info("command reply:\n stdin:{0}\n stdout:{1}\n stderr:{2}".format(
            None,
            stdout.read().decode('utf-8'),
            stderr.read().decode('utf-8')))

    def test_runShellCommandWithSudo(self):
        command = "sudo -S docker run -ti --rm --privileged --name=name1 " \
            + "-v /mnt/huge_1GB:/dev/hugepages " \
            + "-v /tmp/:/tmp/ dpdk-app-testpmd " \
            + "./build/app/testpmd -l 0-1 -n 1 -m 1024 " \
            + "--no-pci " \
            + "--vdev=net_virtio_user0,path=/tmp/vsock_ecc5e758-e1ff-11ea-bb15-1866da864c17_0 " \
            + "--vdev=net_virtio_user1,path=/tmp/vsock_ecc5e758-e1ff-11ea-bb15-1866da864c17_1 " \
            + "--file-prefix=virtio --log-level=8 -- --txqflags=0xf00 " \
            + "--disable-hw-vlan --forward-mode=io --port-topology=chained " \
            + "--total-num-mbufs=2048 -a "
        try:
            shellCmdRply = self.sshA.runShellCommandWithSudo(command,1)
            stdin = shellCmdRply['stdin']
            stdout = shellCmdRply['stdout']
            stderr = shellCmdRply['stderr']
            logging.info("command reply:\n stdin:{0}\n stdout:{1}\n stderr:{2}".format(
                None,
                stdout.read().decode('utf-8'),
                stderr.read().decode('utf-8')))
        except:
            pass
        finally:
            pass