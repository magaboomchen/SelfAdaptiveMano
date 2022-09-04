import json

from django.http import HttpRequest, JsonResponse
from django.shortcuts import render

from sam.base.command import CommandReply
from sam.dashboard.backend.dashboard.message import Requester


def add_sfci(request: HttpRequest):
    try:
        reply: CommandReply = Requester.add_sfci()
        return JsonResponse(reply.attributes)
    except Exception as e:
        return JsonResponse(str(e), status=500, safe=False)


def sfc_view(request: HttpRequest):
    if request.method == "GET":
        return get_sfcs(request)
    elif request.method == "POST":
        return add_sfc(request)
    elif request.method == "DELETE":
        return del_sfc(request)
    else:
        return JsonResponse(None, status=400, safe=False)


def add_sfc(request: HttpRequest):
    req = json.loads(request.body.decode())
    Requester.add_sfc(req)
    return JsonResponse(None, status=200, safe=False)


def get_sfcs(request: HttpRequest):
    sfcs = Requester.get_sfc()
    return JsonResponse(sfcs, status=200, safe=False)


def del_sfc(request: HttpRequest):
    Requester.del_sfc(request.GET.get('sfc_uuid'))
    return JsonResponse(None, status=200, safe=False)
