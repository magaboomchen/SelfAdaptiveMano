#!/usr/bin/python
# -*- coding: UTF-8 -*-

import os
import logging
from logging import handlers


class LoggerConfigurator(object):
    level_relations = {
        'debug':logging.DEBUG,
        'info':logging.INFO,
        'warning':logging.WARNING,
        'error':logging.ERROR,
        'crit':logging.CRITICAL
    }

    def __init__(self, loggerName, directory=None, filename=None,
            level='info',
            fmt='%(asctime)s - %(filename)s[line:%(lineno)d]' \
                '- %(levelname)s:\t%(message)s',
            when='D', interval=1, backCount=7):

        if directory != None and not os.path.exists(directory):
            try:
                os.mkdir(directory)
            except OSError as ex: 
                template = "An exception of type {0} occurred. Arguments:\n{1!r}"
                message = template.format(type(ex).__name__, ex.args)
                logging.error("Logger occure error: {0}".format(message))

        self.logger = logging.getLogger(loggerName)
        self.logger.setLevel(self.level_relations.get(level))

        format_str = logging.Formatter(fmt)
        sh = logging.StreamHandler() # print to screen
        sh.setFormatter(format_str)
        self.logger.addHandler(sh)

        if directory != None and filename != None:
            self.logFilePath = directory + '/' + filename
            th = handlers.TimedRotatingFileHandler(filename=self.logFilePath,
                when=when, interval=interval, backupCount=backCount,
                encoding='utf-8')
            # backupCount: the max log file number
            # when: is the unit of interval
            # S second
            # M Mmniute
            # H hour
            # D day
            # W week
            # midnight
            th.setFormatter(format_str)
            self.logger.addHandler(th)

    def getLogger(self):
        return self.logger


if __name__ == '__main__':
    logConfigur = LoggerConfigurator('logger', './log', 'all.log', level='debug')
    logger = logConfigur.getLogger()
    logger.debug('debug')
    logger.info('info')
    logger.warning('warning')
    logger.error('error')
    logger.critical('critic')
