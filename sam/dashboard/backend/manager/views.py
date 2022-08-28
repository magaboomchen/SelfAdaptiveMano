import json

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from sam.base.command import CommandReply
from sam.dashboard.backend.dashboard.message import Requester


def add_sfci(request: HttpRequest):
    try:
        reply:CommandReply = Requester.add_sfci()
        return HttpResponse(json.dumps(reply.attributes))
    except Exception as e:
        return HttpResponse(str(e), status=500)
