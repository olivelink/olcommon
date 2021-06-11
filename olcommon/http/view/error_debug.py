# -*- coding:utf-8 -*-

from . import error_non_debug
from pyramid.view import exception_view_config
from pyramid.view import forbidden_view_config
from pyramid.view import notfound_view_config


@exception_view_config(renderer="templates/error.pt", route_name="test")
@notfound_view_config(renderer="templates/error.pt", route_name="test")
@forbidden_view_config(renderer="templates/error.pt", route_name="test")
def error(context, request):
    """Allow for rendering the errors on develop but just in the test route"""
    return error_non_debug.error(context, request)
