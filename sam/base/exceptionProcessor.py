#!/usr/bin/python
# -*- coding: UTF-8 -*-

import traceback


class ExceptionProcessor(object):
    def __init__(self, logger):
        self.logger = logger

    def logException(self, ex, note=None):
        template = "An exception of type {0} occurred. Arguments:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        self.logger.error("{0}: {1}".format(note, message))
        self.logger.error(
            "str(Exception):\t{0}\n" \
            "str(ex):\t\t{1}\n" \
            "repr(ex):\t{2}\n" \
            "ex.message:\t{3}\n" \
            "traceback.print_exc():{4}\n" \
            "traceback.format_exc():{5}".format(
                str(Exception), str(ex), repr(ex),
                message, traceback.print_exc(),
                traceback.format_exc()
            )
        )