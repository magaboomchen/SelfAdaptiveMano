import json
import uuid
from typing import Dict

from django.http import HttpRequest, HttpResponse

from sam.base.command import Command, CMD_TYPE_ADD_SFC
from sam.base.link import Link
from sam.base.messageAgent import SIMULATOR_ZONE
from sam.base.rateLimiter import RateLimiterConfig
from sam.base.routingMorphic import RoutingMorphic
from sam.base.server import Server
from sam.base.sfc import SFCI, APP_TYPE_NORTHSOUTH_WEBSITE, SFC
from sam.base.slo import SLO
from sam.base.switch import Switch
from sam.base.test.fixtures.ipv4MorphicDict import ipv4MorphicDictTemplate
from sam.base.vnf import VNF_TYPE_RATELIMITER, VNF, PREFERRED_DEVICE_TYPE_SERVER, VNFI_RESOURCE_QUOTA_SMALL
from sam.dashboard.backend.dashboard.message import Requester
from sam.test.testBase import WEBSITE_REAL_IP


def get_server_set(request: HttpRequest):
    try:
        reply = Requester.get_server_set()
        servers: Dict[int, Dict] = reply.attributes['servers']
        res = []
        for server_id, server_info in servers.items():
            server: Server = server_info['server']
            res.append({
                'id': server_id,
                'active': server_info['Active'],
                'type': server.getServerType(),
                'max_cores': server.getMaxCores() + 2,
                'max_memory': server.getMaxMemory(),
                'cpu_util': server.getCpuUtil(),
                'huge_page_total': server.getHugepagesTotal(),
                'huge_page_free': server.getHugepagesFree(),
                'huge_page_size': server.getHugepagesSize(),
            })
        return HttpResponse(json.dumps(res))
    except Exception as e:
        return HttpResponse(str(e), status=500)


def get_links(request: HttpRequest):
    try:
        reply = Requester.get_topo()
        links = reply.attributes['links']
        res = []
        for (src_id, dst_id), link_info in links.items():
            link: Link = link_info['link']
            res.append({
                'src': src_id,
                'dst': dst_id,
                'active': link_info['Active'],
                'util': link.utilization,
                'bandwidth': link.bandwidth,
            })
        return HttpResponse(json.dumps(res))
    except Exception as e:
        return HttpResponse(str(e), status=500)


def get_switches(request: HttpRequest):
    try:
        reply = Requester.get_topo()
        switches = reply.attributes['switches']
        res = []
        for switch_id, switch_info in switches.items():
            switch: Switch = switch_info['switch']
            res.append({
                'id': switch_id,
                'active': switch_info['Active'],
                'type': switch.switchType,
                'tcam_usage': switch.tcamUsage,
                'tcam_size': switch.tcamSize,
                'lan_net': switch.lanNet
            })
        return HttpResponse(json.dumps(res))
    except Exception as e:
        return HttpResponse(str(e), status=500)


def get_sfcis(request: HttpRequest):
    try:
        reply = Requester.get_sfcis()
        sfcis: Dict[str, SFCI] = reply.attributes['sfcisDict']
        res = []
        for sfci_id, sfci in sfcis.items():
            res.append({
                'id': sfci_id,
                'sfci': sfci.to_dict()
            })
            print(sfci.to_dict())
        return HttpResponse(json.dumps(res, cls=MyEncoder))
    except Exception as e:
        return HttpResponse(str(e), status=500)


def add_sfc(request: HttpRequest):
    pass


class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return obj.__str__()
        if isinstance(obj, RateLimiterConfig):
            return vars(obj)
        if isinstance(obj, bytes):
            return str(obj, encoding='utf-8')
        if isinstance(obj, int):
            return int(obj)
        elif isinstance(obj, float):
            return float(obj)
        else:
            return super(MyEncoder, self).default(obj)
