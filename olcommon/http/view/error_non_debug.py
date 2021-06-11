# -*- coding:utf-8 -*-

from pyramid.view import exception_view_config
from pyramid.view import forbidden_view_config
from pyramid.view import notfound_view_config

import pyramid.httpexceptions


@exception_view_config(renderer="templates/error.pt")
@notfound_view_config(renderer="templates/error.pt")
@forbidden_view_config(renderer="templates/error.pt")
def error(context, request):
    """Generic error handeling"""
    if isinstance(context, pyramid.httpexceptions.HTTPException):
        request.response.status_code = context.code
    else:
        request.response.status_code = 500
    return {}
