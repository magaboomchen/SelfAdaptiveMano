#!/usr/bin/python
# -*- coding: UTF-8 -*-

import random
from getopt import getopt
from sam.simulator.simulatorInfoBaseMaintainer import SimulatorInfoBaseMaintainer

handlers = {}


def op_handler(cmd_type, cmd_str, sib):
    # type: (str, str, SimulatorInfoBaseMaintainer) -> None
    if cmd_type not in handlers.keys():
        raise ValueError('Unknown commend type.')
    try:
        handlers[cmd_type](cmd_str.split(' ')[1:], sib)
    except ValueError:
        raise ValueError(cmd_str)


def add_op_handler(cmd_type):
    def decorator(handler):
        handlers[cmd_type] = handler

    return decorator


@add_op_handler('reset')
def reset_handler(cmd_list, sib):
    # type: (list, SimulatorInfoBaseMaintainer) -> None
    opt, arg = getopt(cmd_list, '', ())
    if not opt and not arg:
        sib.reset()
    else:
        raise ValueError


@add_op_handler('load')
def load_handler(cmd_list, sib):
    # type: (list, SimulatorInfoBaseMaintainer) -> None
    opt, arg = getopt(cmd_list, '', ())
    if not opt and len(arg) == 1:  # load <filename>
        sib.loadTopology(arg[0])
    else:
        raise ValueError


@add_op_handler('server')
def server_handler(cmd_list, sib):
    # type: (list, SimulatorInfoBaseMaintainer) -> None
    opt, arg = getopt(cmd_list, '', ())
    if not opt and len(arg) == 2 and arg[1] in ('up', 'down'):  # server <serverID> up|down
        server_id = int(arg[0])
        sib.servers[server_id]['Active'] = (arg[1].lower() == 'up')
    else:
        raise ValueError


@add_op_handler('switch')
def switch_handler(cmd_list, sib):
    # type: (list, SimulatorInfoBaseMaintainer) -> None
    opt, arg = getopt(cmd_list, '', ())
    if not opt and len(arg) == 2 and arg[1] in ('up', 'down'):  # switch <switchID> up|down
        switch_id = int(arg[0])
        sib.switches[switch_id]['Active'] = (arg[1].lower() == 'up')
    else:
        raise ValueError


@add_op_handler('link')
def link_handler(cmd_list, sib):
    # type: (list, SimulatorInfoBaseMaintainer) -> None
    opt, arg = getopt(cmd_list, '', ())
    if not opt and len(arg) == 3 and arg[2] in ('up', 'down'):  # link <srcID> <dstID> up|down
        src_id = int(arg[0])
        dst_id = int(arg[1])
        sib.links[(src_id, dst_id)]['Active'] = (arg[2].lower() == 'up')
    else:
        raise ValueError


@add_op_handler('traffic')
def traffic_handler(cmd_list, sib):
    # type: (list, SimulatorInfoBaseMaintainer) -> None
    opt, arg = getopt(cmd_list[1:], '', ('trafficPattern=', 'value=', 'min=', 'max=', 'pktSize='))
    traffic_id = cmd_list[0]
    opt = dict(opt)
    # traffic <trafficID> --trafficPattern constant --value <value in Mbps>:
    if not arg and '--trafficPattern' in opt and opt['--trafficPattern'] == 'constant' and '--value' in opt:
        sib.flows[traffic_id]['bw'] = lambda: float(opt['--value'])

    # traffic <trafficID> --trafficPattern uniform --min <value> --max <value>:
    elif not arg and '--trafficPattern' in opt \
            and opt['--trafficPattern'] == 'uniform' and '--min' in opt and '--max' in opt:
        sib.flows[traffic_id]['bw'] = lambda: (
                float(opt['--min']) + (float(opt['--max']) - float(opt['--min'])) * random.random())

    # traffic <trafficID> --pktSize <value in Bytes>:
    elif not arg and '--pktSize' in opt:
        sib.flows[traffic_id]['pkt_size'] = int(opt['--pktSize'])
    else:
        raise ValueError


@add_op_handler('add')
def add_handler(cmd_list, sib):
    # type: (list, SimulatorInfoBaseMaintainer) -> None
    obj_type = cmd_list[0]
    if obj_type != 'traffic':
        raise ValueError
    traffic_id = cmd_list[1]
    sfci_id = int(cmd_list[2])
    dir_id = int(cmd_list[3])
    opt, arg = getopt(cmd_list[4:], '', ())
    if not arg and 'trafficRate' in opt:  # add traffic <trafficID> <sfciID> <dirID> --trafficRate <value in Mbps>
        if traffic_id in sib.flows:
            raise KeyError(traffic_id)
        sib.flows[traffic_id] = {'bw': (lambda: float(opt['--trafficRate'])), 'pkt_size': 500,
                                 'sfciID': sfci_id, 'dirID': dir_id}
        sib.sfcis[sfci_id]['traffics'][dir_id].add(traffic_id)
    else:
        raise ValueError


@add_op_handler('del')
def del_handler(cmd_list, sib):
    # type: (list, SimulatorInfoBaseMaintainer) -> None
    obj_type = cmd_list[0]
    if obj_type != 'traffic':
        raise ValueError
    traffic_id = cmd_list[1]
    opt, arg = getopt(cmd_list[2], '', ())
    if not opt and not arg:  # del traffic <trafficID>
        sfci_id = sib.flows[traffic_id]['sfciID']
        dir_id = sib.flows[traffic_id]['dirID']
        sib.sfcis[sfci_id]['traffics'][dir_id].remove(traffic_id)
        sib.flows.pop(traffic_id)
    else:
        raise ValueError
