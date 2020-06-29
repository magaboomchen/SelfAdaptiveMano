# Copyright 2015 gRPC authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Modify: The Python implementation of the GRPC helloworld.Greeter client."""


from __future__ import print_function
import logging

import grpc

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) )
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/builtin_pb/" )

import service_pb2
import service_pb2_grpc
import bess_msg_pb2
import module_msg_pb2
import ports.port_msg_pb2 as port_msg_pb2

from google.protobuf.any_pb2 import Any

import socket



def aton(ip):
     return socket.inet_aton(ip)

def ntohl(num):
     return socket.ntohl(num)

def htonl(num):
     return socket.htonl(num)

def initConf():
    # NOTE(gRPC Python Team): .close() is possible on a channel and should be
    # used in circumstances in which the with statement does not fit the needs
    # of the code.
    with grpc.insecure_channel('192.168.122.134:10514') as channel:
        stub = service_pb2_grpc.BESSControlStub(channel)
        response = stub.GetVersion(bess_msg_pb2.EmptyRequest())
        logging.info("Greeter client received: " + response.version)

        stub.PauseAll(bess_msg_pb2.EmptyRequest())
        stub.ResetAll(bess_msg_pb2.EmptyRequest())
        
        response = stub.ListDrivers(bess_msg_pb2.EmptyRequest())
        for i in response.driver_names:
            logging.info("List Drivers: " + str(i))

        # NIC
        ## myport::PMDPort(port_id=0, num_inc_q=1, num_out_q=1)
        argument = Any()
        argument.Pack( port_msg_pb2.PMDPortArg(loopback=True,port_id=0,vlan_offload_rx_strip=False,vlan_offload_rx_filter=False,vlan_offload_rx_qinq =False) )
        response = stub.CreatePort(bess_msg_pb2.CreatePortRequest(name='myport',driver='PMDPort',num_inc_q=1,num_out_q=1, size_inc_q=0, size_out_q=0, arg=argument))
        if response.error.code != 0:
            logging.error( str(response.error) )
        else:
            logging.info("CreatePortResponse -- name: " + response.name + " mac_addr: " + response. mac_addr)

        ## input0::QueueInc(port=myport, qid=0)
        argument = Any()
        argument.Pack( module_msg_pb2.QueueIncArg(port='myport', qid=0))
        response = stub.CreateModule(bess_msg_pb2.CreateModuleRequest(name='input0',mclass='QueueInc',arg=argument))
        if response.error.code != 0:
            logging.error( str(response.error) )
        else:
            logging.info('CreateModuleResponse -- name: ' + response.name )

        ## output0::QueueOut(port=myport, qid=0)
        argument = Any()
        argument.Pack( module_msg_pb2.QueueOutArg(port='myport', qid=0))
        response = stub.CreateModule(bess_msg_pb2.CreateModuleRequest(name='output0',mclass='QueueOut',arg=argument))
        if response.error.code != 0:
            logging.error( str(response.error) )
        else:
            logging.info('CreateModuleResponse -- name: ' + response.name )

        # VXLAN VNI Classifier
        ## em::ExactMatch(fields=[{'offset':23, 'num_bytes':1},{'offset':30, 'num_bytes':4},{'offset':45, 'num_bytes':4}])
        argument = Any()
        argument.Pack( module_msg_pb2.ExactMatchArg( fields=[{'offset':23, 'num_bytes':1},{'offset':30, 'num_bytes':4},{'offset':45, 'num_bytes':4}] ))
        response = stub.CreateModule(bess_msg_pb2.CreateModuleRequest(name='em',mclass='ExactMatch',arg=argument))
        if response.error.code != 0:
            logging.error( str(response.error) )
        else:
            logging.info('CreateModuleResponse -- name: ' + response.name )
        
        # rule 1
        ## em.set_default_gate(gate=0)
        argument = Any()
        argument.Pack( module_msg_pb2.ExactMatchCommandSetDefaultGateArg(gate=0) )
        response = stub.ModuleCommand(bess_msg_pb2.CommandRequest(name='em',cmd='set_default_gate',arg=argument))
        if response.error.code != 0:
            logging.error( str(response.error) )
        else:
            logging.info('CreateModuleResponse -- data: ' + str(response.data) )

        # rule 2
        ## em.add(fields=[{'value_int':17}, {'value_bin':aton('192.168.122.111')}, {'value_int':htonl(999)}], gate=1)
        # argument = Any()
        # argument.Pack( module_msg_pb2.ExactMatchCommandAddArg( gate=1, fields=[{'value_int':17}, {'value_bin':aton('192.168.122.111')}, {'value_int':htonl(999)}] ) )
        # response = stub.ModuleCommand(bess_msg_pb2.CommandRequest(name='em',cmd='add',arg=argument))
        # if response.error.code != 0:
        #     logging.error( str(response.error) )
        # else:
        #     logging.info('CreateModuleResponse -- data: ' + str(response.data) )

        # Merge
        ## outmerge::Merge() -> output0
        argument = Any()
        argument.Pack( module_msg_pb2.MergeArg( ))
        response = stub.CreateModule(bess_msg_pb2.CreateModuleRequest(name='outmerge',mclass='Merge',arg=argument))
        if response.error.code != 0:
            logging.error( str(response.error) )
        else:
            logging.info('CreateModuleResponse -- name: ' + response.name )

        # Sink
        stub.CreateModule(bess_msg_pb2.CreateModuleRequest(name='Sink1',mclass='Sink'))
        ### stub.CreateModule(bess_msg_pb2.CreateModuleRequest(name='Sink2',mclass='Sink'))
        
        # Connection
        ## input0 -> em
        stub.ConnectModules(bess_msg_pb2.ConnectModulesRequest(m1='input0',m2='em',ogate=0,igate=0))
 
        ## em:0 -> Sink()
        stub.ConnectModules(bess_msg_pb2.ConnectModulesRequest(m1='em',m2='Sink1',ogate=0,igate=0))

        ## em:1 -> Sink()
        ### stub.ConnectModules(bess_msg_pb2.ConnectModulesRequest(m1='em',m2='Sink2',ogate=1,igate=0))

        ## outmerge -> output0
        stub.ConnectModules(bess_msg_pb2.ConnectModulesRequest(m1='outmerge',m2='output0',ogate=0,igate=0))

        stub.ResumeAll(bess_msg_pb2.EmptyRequest())

        # Backup
        #response = stub.ListMclass(bess_msg_pb2.EmptyRequest())
        #for i in response.names:
        #    logging.info("List Mclass: " + str(i))

        #response = stub.ListModules(bess_msg_pb2.EmptyRequest())
        #for i in response.modules:
        #    logging.info("List Modules: " + str(i))


def addSFC():
    with grpc.insecure_channel('192.168.122.134:10514') as channel:
        stub = service_pb2_grpc.BESSControlStub(channel)
        response = stub.GetVersion(bess_msg_pb2.EmptyRequest() )
        logging.info("stop.")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    initConf()
    addSFC()