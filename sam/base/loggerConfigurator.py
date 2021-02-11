#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
There may be a bug in LoggerConfigurator
It will consume a lot of memory!
'''

import os
import random
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

        self.loggerName = loggerName
        self._appendLoggerNameSuffix()
        self.filename = filename
        # self._appendFileNameSuffix()
        self.logger = logging.getLogger(self.loggerName)
        self.logger.setLevel(self.level_relations.get(level))

        format_str = logging.Formatter(fmt)
        sh = logging.StreamHandler() # print to screen
        sh.setFormatter(format_str)
        self.logger.addHandler(sh)
        sh.close()

        if directory != None and self.filename != None:
            self.logFilePath = directory + '/' + self.filename
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
            th.close()

    def getLogger(self):
        return self.logger

    def _appendLoggerNameSuffix(self):
        suffix = ''.join(random.sample(['z','y','x','w','v','u','t','s','r','q','p','o','n','m','l','k','j','i','h','g','f','e','d','c','b','a'], 5))
        self.loggerName = self.loggerName + "_" + suffix

    def _appendFileNameSuffix(self):
        suffix = ''.join(random.sample(['z','y','x','w','v','u','t','s','r','q','p','o','n','m','l','k','j','i','h','g','f','e','d','c','b','a'], 5))
        self.filename = self.filename + "._" + suffix


if __name__ == '__main__':
    logConfigur = LoggerConfigurator('logger', './log', 'all.log', level='debug')
    logger = logConfigur.getLogger()
    logger.debug('debug')
    logger.info('info')
    logger.warning('warning')
    logger.error('error')
    logger.critical('critic')
