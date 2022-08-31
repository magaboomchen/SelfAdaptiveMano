#!/usr/bin/python
# -*- coding: UTF-8 -*-
import random
import time
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


@add_op_handler('save')
def save_handler(cmd_list, sib):
    # type: (list, SimulatorInfoBaseMaintainer) -> None
    opt, arg = getopt(cmd_list, '', ())
    if not opt and len(arg) == 1:  # load <filename>
        sib.saveTopology(arg[0])
    else:
        raise ValueError


@add_op_handler('exit')
def exit_handler(cmd_list, sib):
    # type: (list, SimulatorInfoBaseMaintainer) -> None
    raise SystemExit


@add_op_handler('server')
def server_handler(cmd_list, sib):
    # type: (list, SimulatorInfoBaseMaintainer) -> None
    server_id = int(cmd_list[0])
    cmd = cmd_list[1]
    opt, arg = getopt(cmd_list[2:], '', ('pattern=', 'value=', 'min=', 'max='))
    opt = dict(opt)
    if not opt and not arg and cmd in ('up', 'down'):  # server <serverID> up|down
        sib.servers[server_id]['Active'] = (cmd == 'up')
    elif not arg and cmd in ('cpu', 'mem'):
        sib.bgProcesses.setdefault(server_id, {'cpu': lambda: 0, 'mem': lambda: 0})
        if opt['--pattern'] == 'constant' and '--value' in opt:
            func = lambda: float(opt['--value'])
        elif opt['--pattern'] == 'uniform' and '--max' in opt and '--min' in opt:
            func = lambda: (float(opt['--min']) + random.random() * (float(opt['--max']) - float(opt['--min'])))
        else:
            raise ValueError
        sib.bgProcesses[server_id][cmd] = func
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
    traffic_id = int(cmd_list[0])
    opt = dict(opt)
    has_change = False
    # traffic <trafficID> --trafficPattern constant --value <value in Mbps>:
    if not arg and '--trafficPattern' in opt and opt['--trafficPattern'] == 'constant' and '--value' in opt:
        sib.update_flow(sib.flows[traffic_id])
        sib.flows[traffic_id]['bw'] = lambda: float(opt['--value'])
        has_change = True

    # traffic <trafficID> --trafficPattern uniform --min <value> --max <value>:
    elif not arg and '--trafficPattern' in opt \
            and opt['--trafficPattern'] == 'uniform' and '--min' in opt and '--max' in opt:
        sib.update_flow(sib.flows[traffic_id])
        sib.flows[traffic_id]['bw'] = lambda: (
                float(opt['--min']) + (float(opt['--max']) - float(opt['--min'])) * random.random())
        has_change = True

    # traffic <trafficID> --pktSize <value in Bytes>:
    if not arg and '--pktSize' in opt:
        sib.update_flow(sib.flows[traffic_id])
        sib.flows[traffic_id]['pkt_size'] = int(opt['--pktSize'])
        has_change = True

    if not has_change:
        raise ValueError


@add_op_handler('add')
def add_handler(cmd_list, sib):
    # type: (list, SimulatorInfoBaseMaintainer) -> None
    obj_type = cmd_list[0]
    if obj_type != 'traffic':
        raise ValueError
    traffic_id = int(cmd_list[1])
    sfci_id = int(cmd_list[2])
    dir_id = int(cmd_list[3])
    opt, arg = getopt(cmd_list[4:], '', ('trafficRate=',))
    opt = dict(opt)
    if not arg and '--trafficRate' in opt:  # add traffic <trafficID> <sfciID> <dirID> --trafficRate <value in Mbps>
        if traffic_id in sib.flows:
            raise KeyError(traffic_id)
        sib.flows[traffic_id] = {'bw': (lambda: float(opt['--trafficRate'])), 'pkt_size': 500,
                                 'sfciID': sfci_id, 'dirID': dir_id, 'traffic': 0, 'pkt': 0, 'timestamp': time.time(),
                                 'del': False}
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
        sib.update_flow(sib.flows[traffic_id])
        sib.flows[traffic_id]['del'] = True
    else:
        raise ValueError
