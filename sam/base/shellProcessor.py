import psutil
import subprocess
import logging

class ShellProcessor(object):
    def listRunningProcess(self):
        logging.info("List running process.")
        for p in psutil.process_iter(attrs=['pid', 'name']):
            logging.info(p)

    def isProcessRun(self,processName):
        for p in psutil.process_iter(attrs=['pid', 'name']):
            if processName in p.info['name']:
                logging.info(processName + " has already running.")
                return True
        return False

    def runProcess(self,filePath):
        if root == True:
            user = "sudo "
        else:
            user = ""
        out_bytes = subprocess.check_output(
            [ user + filePath], shell=True)

    def killProcess(self,processName):
        for p in psutil.process_iter(attrs=['pid', 'name']):
            if processName in p.info['name']:
                pid = int(p.info['pid'])
                out_bytes = subprocess.check_output(
                    ["sudo kill " + str(pid)], shell=True)

    def isPythonScriptRun(self,moduleName):
        for p in psutil.process_iter(attrs=['pid', 'name', 'cmdline']):
            logging.info(p)
            if p.info['name'] == "python":
                for cmdline in p.info['cmdline']:
                    if cmdline.count(moduleName) > 0:
                        return True
        return False

    def runPythonScript(self, filePath, root=False):
        if root == True:
            user = "sudo "
        else:
            user = ""
        subprocess.Popen(
            [ user + " python " + filePath], shell=True)

    def killPythonScript(self,moduleName):
        for p in psutil.process_iter(attrs=['pid', 'name', 'cmdline']):
            logging.info(p)
            if p.info['name'] == "python":
                for cmdline in p.info['cmdline']:
                    if cmdline.find(moduleName) != -1:
                        pid = int(p.info['pid'])
                        out_bytes = subprocess.check_output(
                            ["sudo kill " + str(pid)], shell=True)
    
    def runShellCommand(self,shellCmd):
        return subprocess.check_output([shellCmd], shell=True)