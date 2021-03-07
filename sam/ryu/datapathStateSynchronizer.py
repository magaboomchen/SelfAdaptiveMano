#!/usr/bin/python
# -*- coding: UTF-8 -*-

from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3

from sam.ryu.baseApp import BaseApp
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.exceptionProcessor import ExceptionProcessor


class DatapathStateSynchronizer(BaseApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(DatapathStateSynchronizer, self).__init__(*args, **kwargs)
        logConfigur = LoggerConfigurator(__name__, './log',
                            'datapathStateSynchronizer.log', level='debug')
        self.logger = logConfigur.getLogger()
        self.recvBarrier = {}
        self.logger.info(" DatapathStateSynchronizer Start! ")

    def sendBarrierRequest(self, datapath):
        try:
            self.logger.debug("send barrier")
            ofp_parser = datapath.ofproto_parser
            req = ofp_parser.OFPBarrierRequest(datapath)
            dpid = datapath.id
            self.recvBarrier[dpid] = False
            self.logger.debug("send barrier request to dpid: {0}".format(dpid))
            datapath.send_msg(req)
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex)

    def getBarrierState(self, datapath):
        dpid = datapath.id
        return self.recvBarrier[dpid]

    @set_ev_cls(ofp_event.EventOFPBarrierReply, MAIN_DISPATCHER)
    def barrier_reply_handler(self, ev):
        try:
            self.logger.debug("barrier reply handler")
            datapath = ev.msg.datapath
            dpid = datapath.id
            self.logger.debug('OFPBarrierReply received from dpid:{0}'.format(dpid))
            self.recvBarrier[dpid] = True
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex)
