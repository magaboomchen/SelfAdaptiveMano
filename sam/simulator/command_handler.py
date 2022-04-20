#!/usr/bin/python
# -*- coding: UTF-8 -*-
import random

from sam.base.command import Command, CMD_TYPE_ADD_SFC, CMD_TYPE_DEL_SFC, CMD_TYPE_ADD_SFCI, \
    CMD_TYPE_DEL_SFCI, CMD_TYPE_GET_SERVER_SET, CMD_TYPE_GET_TOPOLOGY, CMD_TYPE_GET_FLOW_SET
from sam.base.flow import Flow
from sam.base.path import DIRECTION2_PATHID_OFFSET, DIRECTION1_PATHID_OFFSET
from sam.base.server import Server, SERVER_TYPE_CLASSIFIER, SERVER_TYPE_NFVI
from sam.base.sfc import SFC, SFCI
from sam.base.switch import Switch
from sam.base.vnf import VNFI
from sam.simulator.nf import NF
from sam.simulator.simulatorInfoBaseMaintainer import SimulatorInfoBaseMaintainer

handlers = {}


def add_command_handler(cmd_type):
    def decorator(handler):
        handlers[cmd_type] = handler

    return decorator


def command_handler(cmd, sib):
    # type: (Command, SimulatorInfoBaseMaintainer) -> dict
    if cmd.cmdType not in handlers.keys():
        raise ValueError("Unknown command type.")
    attributes = handlers[cmd.cmdType](cmd, sib)

    return attributes


def check_sfc(sfc, sib):
    directions = sfc.directions
    assert len(directions) in {1, 2}
    assert [direction['ID'] for direction in directions] == list(range(len(directions)))
    for direction in directions:
        ingress = direction['ingress']
        ingressID = ingress.getServerID()
        egress = direction['egress']
        egressID = egress.getServerID()
        assert ingressID in sib.servers and sib.servers[ingressID][
            'server'].getServerType() == SERVER_TYPE_CLASSIFIER
        assert egressID in sib.servers and sib.servers[egressID][
            'server'].getServerType() == SERVER_TYPE_CLASSIFIER


def remove_sfci(sfc, sfci, sib):
    directions = sfc.directions
    sfciID = sfci.sfciID
    vnfiSequence = sfci.vnfiSequence
    forwardingPathSet = sfci.forwardingPathSet
    primaryForwardingPath = forwardingPathSet.primaryForwardingPath
    # release resources
    # server core, switch tcam, switch nextHop, (server)link usedBy
    direction = directions[0]  # [d for d in directions if d['ID']==0][0]
    dirID = 0
    pathlist = primaryForwardingPath[DIRECTION1_PATHID_OFFSET]
    for stage, path in enumerate(pathlist):
        if stage != len(pathlist) - 1:  # dst is vnfi
            serverID = path[-1][1]
            assert serverID in sib.vnfis.keys()
            for i in range(len(sib.vnfis[serverID])):
                vnfi = sib.vnfis[i]
                if vnfi['sfciID'] == sfciID and vnfi['stage'] == stage and vnfi['vnfi'].vnfType == vnfiSequence[stage][
                    0].vnfType:
                    sib.vnfis.pop(i)
                    break
            else:
                raise ValueError('no vnfi to remove on server %d vnfType %d', serverID, vnfiSequence[stage][0].vnfType)
    for direction in directions:
        dirID = direction['ID']
        if dirID == 0:
            pathlist = primaryForwardingPath[DIRECTION1_PATHID_OFFSET]
        elif dirID == 1:
            pathlist = primaryForwardingPath[DIRECTION2_PATHID_OFFSET]
        for stage, path in enumerate(pathlist):
            for hop, (_, switchID) in enumerate(path):
                if hop != 0 and hop != len(path) - 1:  # switchID is a switch, not server
                    switchInfo = sib.switches[switchID]
                    switch = switchInfo['switch']
                    if switch.tcamUsage <= 0:
                        raise ValueError('no tcam to release on switch %d', switchID)
                    switch.tcamUsage -= 1
                    switchInfo['Status']['nextHop'].pop((sfciID, dirID, stage, hop))
                if hop != len(path) - 1:
                    srcID = switchID
                    dstID = path[hop + 1][1]
                    if hop == 0:  # server -> switch, switchID is server
                        linkInfo = sib.serverLinks[(srcID, dstID)]
                    elif hop == len(path) - 2:  # switch -> server
                        linkInfo = sib.serverLinks[(srcID, dstID)]
                    else:  # switch -> switch
                        linkInfo = sib.links[(srcID, dstID)]
                    linkInfo['Status']['usedBy'].remove((sfciID, dirID, stage, hop))
    # purge information
    for traffics in sib.sfcis[sfciID]['traffics'].values():
        for trafficID in traffics:
            sib.flows.pop(trafficID)
    sib.sfcis.pop(sfciID)


@add_command_handler(CMD_TYPE_ADD_SFC)
def add_sfc_handler(cmd, sib):
    # type: (Command, SimulatorInfoBaseMaintainer) -> dict
    sfc = cmd.attributes['sfc']  # type: SFC
    sfcUUID = sfc.sfcUUID
    check_sfc(sfc, sib)
    sib.sfcs[sfcUUID] = {'sfc': sfc}

    return {}


@add_command_handler(CMD_TYPE_ADD_SFCI)
def add_sfci_handler(cmd, sib):
    # type: (Command, SimulatorInfoBaseMaintainer) -> dict
    sfc = cmd.attributes['sfc']  # type: SFC
    sfcUUID = sfc.sfcUUID
    directions = sfc.directions
    check_sfc(sfc, sib)
    sfci = cmd.attributes['sfci']  # type: SFCI
    sfciID = sfci.sfciID
    vnfiSequence = sfci.vnfiSequence
    for vnfiSeqStage in vnfiSequence:
        assert len(vnfiSeqStage) == 1  # no backup
        vnfi = vnfiSeqStage[0]  # type: VNFI
        vnfID = vnfi.vnfID
        vnfType = vnfi.vnfType
        vnfiID = vnfi.vnfiID
        node = vnfi.node
        if isinstance(node, Server):
            nodeID = node.getServerID()
            assert nodeID in sib.servers and sib.servers[nodeID][
                'server'].getServerType() == SERVER_TYPE_NFVI
        elif isinstance(node, Switch):
            nodeID = node.switchID
            assert node.programmable
            assert nodeID in sib.switches
        else:
            raise ValueError('vnfi node is neither server nor switch')
    forwardingPathSet = sfci.forwardingPathSet
    mappingType = forwardingPathSet.mappingType
    primaryForwardingPath = forwardingPathSet.primaryForwardingPath
    assert len(primaryForwardingPath) == len(directions)
    for direction in directions:
        dirID = direction['ID']
        if dirID == 0:
            pathlist = primaryForwardingPath[DIRECTION1_PATHID_OFFSET]
        elif dirID == 1:
            pathlist = primaryForwardingPath[DIRECTION2_PATHID_OFFSET]
        else:
            raise ValueError('unknown dirID')
        assert len(pathlist) == len(vnfiSequence) + 1
        ingress = direction['ingress']
        ingressID = ingress.getServerID()
        egress = direction['egress']
        egressID = egress.getServerID()
        assert ingressID == pathlist[0][0][1]
        assert (pathlist[0][0][1], pathlist[0][1][1]) in sib.serverLinks
        assert egressID == pathlist[-1][-1][1]
        assert (pathlist[-1][-2][1], pathlist[-1][-1][1]) in sib.serverLinks
        for i, vnfiSeqStage in enumerate(vnfiSequence) if dirID == 0 else enumerate(reversed(vnfiSequence)):
            vnfi = vnfiSeqStage[0]  # no backup
            node = vnfi.node
            if isinstance(node, Server):
                nodeID = node.getServerID()
            elif isinstance(node, Switch):
                nodeID = node.switchID
            assert pathlist[i][-1][1] == nodeID
            assert pathlist[i + 1][0][1] == nodeID
            assert pathlist[i][-2][1] == pathlist[i + 1][1][1]
            if isinstance(node, Server):
                assert (pathlist[i][-2][1], pathlist[i][-1][1]) in sib.serverLinks
                assert (pathlist[i + 1][0][1], pathlist[i + 1][1][1]) in sib.serverLinks
            elif isinstance(node, Switch):
                assert (pathlist[i][-2][1], pathlist[i][-1][1]) in sib.links
                assert (pathlist[i + 1][0][1], pathlist[i + 1][1][1]) in sib.links
        for path in pathlist:
            for _, switchID in path[1:-1]:
                assert switchID in sib.switches
            for i in range(1, len(path) - 2):
                assert (path[i][1], path[i + 1][1]) in sib.links

    # check and assign resources
    # server core, switch tcam, switch nextHop, (server)link usedBy
    direction = directions[0]  # [d for d in directions if d['ID']==0][0]
    dirID = 0
    pathlist = primaryForwardingPath[DIRECTION1_PATHID_OFFSET]
    for stage, path in enumerate(pathlist):
        if stage != len(pathlist) - 1:  # dst is vnfi
            serverID = path[-1][1]
            vnfi = vnfiSequence[stage][0]
            sib.vnfis.setdefault(serverID, []).append({
                'sfciID': sfciID,
                'stage': stage,
                'vnfi': vnfi,
                'cpu': lambda: (100 * (vnfi.minCPUNum + random.random() * (vnfi.maxCPUNum - vnfi.minCPUNum))),
                'mem': lambda: (vnfi.minMem + random.random() * (vnfi.maxMem - vnfi.minMem)),
            })
    for direction in directions:
        dirID = direction['ID']
        if dirID == 0:
            pathlist = primaryForwardingPath[DIRECTION1_PATHID_OFFSET]
        elif dirID == 1:
            pathlist = primaryForwardingPath[DIRECTION2_PATHID_OFFSET]
        for stage, path in enumerate(pathlist):
            for hop, (_, switchID) in enumerate(path):
                if hop != 0 and hop != len(path) - 1:  # switchID is a switch, not server
                    switchInfo = sib.switches[switchID]
                    switch = switchInfo['switch']
                    if switch.tcamUsage >= switch.tcamSize:
                        raise ValueError('no tcam available on switch %d', switchID)
                    switch.tcamUsage += 1
                    switchInfo['Status']['nextHop'][(sfciID, dirID, stage, hop)] = path[hop + 1][1]
                if hop != len(path) - 1:
                    srcID = switchID
                    dstID = path[hop + 1][1]
                    if hop == 0:  # server -> switch, switchID is server
                        linkInfo = sib.serverLinks[(srcID, dstID)]
                    elif hop == len(path) - 2:  # switch -> server
                        linkInfo = sib.serverLinks[(srcID, dstID)]
                    else:  # switch -> switch
                        linkInfo = sib.links[(srcID, dstID)]
                    linkInfo['Status']['usedBy'].add((sfciID, dirID, stage, hop))
    # store information
    sib.sfcs[sfcUUID] = {'sfc': sfc}
    sib.sfcis[sfciID] = {'sfc': sfc, 'sfci': sfci,
                         'traffics': {direction['ID']: set() for direction in directions}}
    return {}


@add_command_handler(CMD_TYPE_DEL_SFCI)
def del_sfci_handler(cmd, sib):
    # type: (Command, SimulatorInfoBaseMaintainer) -> dict
    sfc = cmd.attributes['sfc']
    sfci = cmd.attributes['sfci']
    remove_sfci(sfc, sfci, sib)
    return {}


@add_command_handler(CMD_TYPE_DEL_SFC)
def del_sfc_handler(cmd, sib):
    # type: (Command, SimulatorInfoBaseMaintainer) -> dict
    sfc = cmd.attributes['sfc']  # type: SFC
    sfcUUID = sfc.sfcUUID
    for sfciID, sfciInfo in sib.sfcis.items():
        if sfciInfo['sfc'].sfcUUID == sfcUUID:
            sfci = sfciInfo['sfci']
            remove_sfci(sfc, sfci, sib)
    sib.sfcs.pop(sfcUUID)
    return {}


@add_command_handler(CMD_TYPE_GET_SERVER_SET)
def get_server_set_handler(cmd, sib):
    # type: (Command, SimulatorInfoBaseMaintainer) -> dict
    # format ref: SeverManager.serverSet, SeverManager._storeServerInfo
    sib.updateServerResource()
    result = {}
    for serverID, serverInfo in sib.servers.items():
        result[serverID] = {'server': serverInfo['server'], 'Active': serverInfo['Active'],
                            'timestamp': serverInfo['timestamp']}
    return {'servers': result}


@add_command_handler(CMD_TYPE_GET_TOPOLOGY)
def get_topology_handler(cmd, sib):
    # type: (Command, SimulatorInfoBaseMaintainer) -> dict
    # see ryu/topoCollector.py -> TopoCollector.get_topology_handler
    sib.updateLinkUtilization()
    switches = {}
    for switchID, switchInfo in sib.switches.items():
        switches[switchID] = {'switch': switchInfo['switch'], 'Active': switchInfo['Active']}
    links = {}
    for (srcNodeID, dstNodeID), linkInfo in sib.links.items():
        links[(srcNodeID, dstNodeID)] = {'link': linkInfo['link'], 'Active': linkInfo['Active']}
    return {'switches': switches, 'links': links}


# @add_commend_handler(CMD_TYPE_GET_SFCI_STATE)
# def get_sfci_state_handler(cmd, sib):
#     # type: (Command, SimulatorInfoBaseMaintainer) -> dict
#     pass
#     # TODO

@add_command_handler(CMD_TYPE_GET_FLOW_SET)
def get_flow_set_handler(cmd, sib):
    # type: (Command, SimulatorInfoBaseMaintainer) -> dict
    result = []
    for sfciID, sfciInfo in sib.sfcis.items():
        sfci = sfciInfo['sfci']
        assert len(sfci.vnfiSequence) == 1  # can only handle single NF instances instead of chains
        sfc = sfciInfo['sfc']
        directions = sfc.directions
        traffics_by_dir = sfciInfo['traffics']

        if 0 in traffics_by_dir:  # forward
            traffic_forward = list(traffics_by_dir[0])
            pathlist = sfci.forwardingPathSet.primaryForwardingPath[DIRECTION1_PATHID_OFFSET]
            path = pathlist[0]
            for i, (_, nodeID) in path:
                if i == 0 or i == len(path) - 1:  # ingress server and vnfi server
                    if not sib.servers[nodeID]['Active']:
                        traffic_forward = []
                else:  # switch
                    if not sib.switches[nodeID]['Active']:
                        traffic_forward = []
                if i == len(path) - 1:
                    pass
                elif i == 0 or i == len(path) - 2:  # server-switch link
                    if not sib.serverLinks[(nodeID, path[i + 1][1])]['Active']:
                        traffic_forward = []
                else:  # switch-switch link
                    if not sib.links[(nodeID, path[i + 1][1])]['Active']:
                        traffic_forward = []
        else:
            traffic_forward = []

        if 1 in traffics_by_dir:  # backward
            traffic_backward = list(traffics_by_dir[1])
            pathlist = sfci.forwardingPathSet.primaryForwardingPath[DIRECTION2_PATHID_OFFSET]
            path = pathlist[0]
            for i, (_, nodeID) in path:
                if i == 0 or i == len(path) - 1:  # ingress server and vnfi server
                    if not sib.servers[nodeID]['Active']:
                        traffic_backward = []
                else:  # switch
                    if not sib.switches[nodeID]['Active']:
                        traffic_backward = []
                if i == len(path) - 1:
                    pass
                elif i == 0 or i == len(path) - 2:  # server-switch link
                    if not sib.serverLinks[(nodeID, path[i + 1][1])]['Active']:
                        traffic_backward = []
                else:  # switch-switch link
                    if not sib.links[(nodeID, path[i + 1][1])]['Active']:
                        traffic_backward = []
        else:
            traffic_backward = []

        if not traffic_forward and not traffic_backward:  # no traffic on this sfci
            continue
        traffics = traffic_forward + traffic_backward
        assert len({sib.flows[trafficID]['pkt_size'] for trafficID in traffics}) == 1
        target = NF(sfci.vnfiSequence[0][0].vnfType, sib.flows[traffics[0]]['pkt_size'],
                    4000000)  # no information about flow_count
        serverID = sfci.vnfiSequence[0][0].node.getServerID()
        switchID = sfci.forwardingPathSet.primaryForwardingPath[DIRECTION2_PATHID_OFFSET][0][-2][
            1]  # last switch on path ingress->vnfi
        serverInfo = sib.servers[serverID]
        server = serverInfo['Server']
        # competitors = []
        # for coreID in server.getCoreNUMADistribution()[serverInfo['uplink2NUMA'][switchID]]:
        #     if coreID in serverInfo['Status']['coreAssign'] and serverInfo['Status']['coreAssign'][coreID][:1] != (
        #             sfciID, 0):  # competitor core on the same NUMA node
        #         c_sfciID = serverInfo['Status']['coreAssign'][coreID][0]
        #         c_sfciInfo = sib.sfcis[c_sfciID]
        #         c_sfci = c_sfciInfo['sfci']
        #         c_sfc = c_sfciInfo['sfc']
        #         c_directions = c_sfc.directions
        #         c_traffics_by_dir = c_sfciInfo['traffics']
        #         if 0 in c_traffics_by_dir:  # forward
        #             c_traffic_forward = list(c_traffics_by_dir[0])
        #             c_pathlist = c_sfci.forwardingPathSet.primaryForwardingPath[DIRECTION1_PATHID_OFFSET]
        #             c_path = c_pathlist[0]
        #             for i, (_, nodeID) in c_path:
        #                 if i == 0 or i == len(c_path) - 1:  # ingress server and vnfi server
        #                     if not sib.servers[nodeID]['Active']:
        #                         c_traffic_forward = []
        #                 else:  # switch
        #                     if not sib.switches[nodeID]['Active']:
        #                         c_traffic_forward = []
        #                 if i == len(c_path) - 1:
        #                     pass
        #                 elif i == 0 or i == len(c_path) - 2:  # server-switch link
        #                     if not sib.serverLinks[(nodeID, c_path[i + 1][1])]['Active']:
        #                         c_traffic_forward = []
        #                 else:  # switch-switch link
        #                     if not sib.links[(nodeID, c_path[i + 1][1])]['Active']:
        #                         c_traffic_forward = []
        #         else:
        #             c_traffic_forward = []
        #
        #         if 1 in c_traffics_by_dir:  # backward
        #             c_traffic_backward = list(c_traffics_by_dir[1])
        #             c_pathlist = c_sfci.forwardingPathSet.primaryForwardingPath[DIRECTION2_PATHID_OFFSET]
        #             c_path = c_pathlist[0]
        #             for i, (_, nodeID) in c_path:
        #                 if i == 0 or i == len(c_path) - 1:  # ingress server and vnfi server
        #                     if not sib.servers[nodeID]['Active']:
        #                         c_traffic_backward = []
        #                 else:  # switch
        #                     if not sib.switches[nodeID]['Active']:
        #                         c_traffic_backward = []
        #                 if i == len(c_path) - 1:
        #                     pass
        #                 elif i == 0 or i == len(c_path) - 2:  # server-switch link
        #                     if not sib.serverLinks[(nodeID, c_path[i + 1][1])]['Active']:
        #                         c_traffic_backward = []
        #                 else:  # switch-switch link
        #                     if not sib.links[(nodeID, c_path[i + 1][1])]['Active']:
        #                         c_traffic_backward = []
        #         else:
        #             c_traffic_backward = []
        #
        #         c_traffics = c_traffic_forward + c_traffic_backward
        #         if c_traffics:  # this competitor has traffic
        #             competitors.append(NF(serverInfo['Status']['coreAssign'][coreID][2],
        #                                   sib.flows[c_traffics[0]]['pkt_size'],
        #                                   4000000))  # no info about flow_count
        input_pps_list = [sib.flows[traffic]['bw']() * 1e6 / 8 / sib.flows[traffic]['pkt_size'] for
                          traffic in traffics]
        input_pps = sum(input_pps_list)
        # response_ratio = min(predict(target, competitors) / input_pps, 1.0)
        response_ratio = min(1.0 / input_pps, 1.0)

        identifierDict = sfc.routingMorphic.getIdentifierDict()
        identifierDict['value'] = sfc.routingMorphic.encodeIdentifierForSFC(sfci.sfciID,
                                                                            sfci.vnfiSequence[0][0].vnfID)
        identifierDict['humanReadable'] = sfc.routingMorphic.value2HumanReadable(identifierDict['value'])

        for i, trafficID in enumerate(traffic_forward):
            pps_in = input_pps_list[i]
            result.append(
                Flow(identifierDict, pps_in / 1e6, pps_in / 1e6 * 8 * sib.flows[trafficID]['pkt_size']))
        for i, trafficID in enumerate(traffic_backward):
            pps_in = input_pps_list[i + len(traffic_forward)]
            result.append(
                Flow(identifierDict, pps_in / 1e6, pps_in / 1e6 * 8 * sib.flows[trafficID]['pkt_size']))

        no_traffic_fw = False
        if 0 in traffics_by_dir:  # forward
            pathlist = sfci.forwardingPathSet.primaryForwardingPath[DIRECTION1_PATHID_OFFSET]
            path = pathlist[1]
            for i, (_, nodeID) in path:
                if i == 0 or i == len(path) - 1:  # ingress server and vnfi server
                    if not sib.servers[nodeID]['Active']:
                        no_traffic_fw = True
                else:  # switch
                    if not sib.switches[nodeID]['Active']:
                        no_traffic_fw = True
                if i == len(path) - 1:
                    pass
                elif i == 0 or i == len(path) - 2:  # server-switch link
                    if not sib.serverLinks[(nodeID, path[i + 1][1])]['Active']:
                        no_traffic_fw = True
                else:  # switch-switch link
                    if not sib.links[(nodeID, path[i + 1][1])]['Active']:
                        no_traffic_fw = True
        else:
            no_traffic_fw = True

        no_traffic_bw = False
        if 1 in traffics_by_dir:  # backward
            pathlist = sfci.forwardingPathSet.primaryForwardingPath[DIRECTION2_PATHID_OFFSET]
            path = pathlist[1]
            for i, (_, nodeID) in path:
                if i == 0 or i == len(path) - 1:  # ingress server and vnfi server
                    if not sib.servers[nodeID]['Active']:
                        no_traffic_bw = True
                else:  # switch
                    if not sib.switches[nodeID]['Active']:
                        no_traffic_bw = True
                if i == len(path) - 1:
                    pass
                elif i == 0 or i == len(path) - 2:  # server-switch link
                    if not sib.serverLinks[(nodeID, path[i + 1][1])]['Active']:
                        no_traffic_bw = True
                else:  # switch-switch link
                    if not sib.links[(nodeID, path[i + 1][1])]['Active']:
                        no_traffic_bw = True
        else:
            no_traffic_bw = True

        if not no_traffic_fw:
            for i, trafficID in enumerate(traffic_forward):
                pps_in = input_pps_list[i]
                result.append(Flow(identifierDict, response_ratio * pps_in / 1e6,
                                   response_ratio * pps_in / 1e6 * 8 * sib.flows[trafficID]['pkt_size']))
        if not no_traffic_bw:
            for i, trafficID in enumerate(traffic_backward):
                pps_in = input_pps_list[i + len(traffic_forward)]
                result.append(Flow(identifierDict, response_ratio * pps_in / 1e6,
                                   response_ratio * pps_in / 1e6 * 8 * sib.flows[trafficID]['pkt_size']))

    return {'flows': result}
