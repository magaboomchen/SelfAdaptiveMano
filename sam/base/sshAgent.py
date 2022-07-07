#!/usr/bin/python
# -*- coding: UTF-8 -*-

import sys
if sys.version > '3':
    import io
    from io import StringIO
else:
    import StringIO
import paramiko
import logging


class SSHAgent(object):
    def __init__(self):
        self.ssh = paramiko.SSHClient()

        logging.getLogger("paramiko").setLevel(logging.ERROR)

    def connectSSH(self, sshUsrname, sshPassword, remoteIP, remoteSSHPort=22):
        self.passwd = sshPassword
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(hostname = remoteIP, port = remoteSSHPort,
            username = sshUsrname, password = sshPassword)

    def connectSSHWithRSA(self, sshUsrname, privateKeyFilePath, remoteIP, remoteSSHPort=22):
        f = open(privateKeyFilePath,'r')
        s = f.read()
        keyfile = StringIO.StringIO(s)
        mykey = paramiko.RSAKey.from_private_key(keyfile)
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(hostname = remoteIP, port = remoteSSHPort,
            username = sshUsrname, pkey=mykey)
        f.close()

    def loadUserPassword(self, sshPassword):
        self.passwd = sshPassword

    def runShellCommand(self,command):
        stdin, stdout, stderr = self.ssh.exec_command(command, get_pty=True)
        return {'stdin':stdin, 'stdout':stdout, 'stderr':stderr}

    def runShellCommandWithSudo(self,command, timeout=None):
        stdin, stdout, stderr = self.ssh.exec_command(command, timeout=timeout,
            get_pty=True)
        stdin.write('{0}\n'.format(str(self.passwd)))
        stdin.flush()
        return {'stdin':stdin, 'stdout':stdout, 'stderr':stderr}

    def disconnectSSH(self):
        self.ssh.close()

    def __del__(self):
        self.ssh.close()