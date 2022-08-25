#!/usr/bin/python
# -*- coding: UTF-8 -*-

from __future__ import print_function
import grpc

import sam.serverController.builtin_pb.service_pb2_grpc as service_pb2_grpc
import sam.serverController.builtin_pb.bess_msg_pb2 as bess_msg_pb2


if __name__ == "__main__":
    serverControlIP = "192.168.0.173"
    bessServerUrl = serverControlIP + ":10514"
    with grpc.insecure_channel(bessServerUrl) as channel:
        stub = service_pb2_grpc.BESSControlStub(channel)
        stub.PauseAll(bess_msg_pb2.EmptyRequest())
        stub.ResumeAll(bess_msg_pb2.EmptyRequest())