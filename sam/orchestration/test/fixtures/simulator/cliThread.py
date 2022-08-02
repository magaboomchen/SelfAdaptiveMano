#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging
import threading

from sam.base.compatibility import screenInput
from sam.base.loggerConfigurator import LoggerConfigurator


class CLIThread(threading.Thread):
    def __init__(self, threadID, sib):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self._sib = sib

        logConfigur = LoggerConfigurator(__name__,
            './log', 'cliThread.log', level='debug')
        self.logger = logConfigur.getLogger()
        self.logger.info("Init cliThread.")

    def run(self):
        self.logger.info("start CLI.")
        while True:
            self.logger.info("Please input data")
            screenInput()

    # TODO：开始实验
    # 生成实验参数，启动实验，保存中间结果，分析结果，保存结果
    # 给定中间结果，分析结果，保存结果

    # TODO: 增加addSFC, addSFCI request
    # 发送给 orchestrator

    # TODO: 增加topology

    # TODO: analysis
    # 暂存 pickle
