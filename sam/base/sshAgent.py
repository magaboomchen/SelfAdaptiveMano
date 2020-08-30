import paramiko

class SSHAgent(object):
    def __init__(self, ):
        self.ssh = paramiko.SSHClient()

    def connectSSH(self,sshUsrname, sshPassword, remoteIP, remoteSSHPort=22):
        self.passwd = sshPassword
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(hostname = remoteIP, port = remoteSSHPort,
            username = sshUsrname, password = sshPassword)

    def runShellCommand(self,command):
        stdin, stdout, stderr = self.ssh.exec_command(command)
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