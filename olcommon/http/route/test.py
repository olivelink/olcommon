# -*- coding: utf-8 -*-

from pyramid.exceptions import HTTPForbidden
from pyramid.exceptions import HTTPNotFound
from pyramid.view import view_config
from pyramid.view import view_defaults


@view_defaults(route_name="test")
class TestView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

    @view_config(name="fail")
    def fail(self):
        """A view which allways fails"""
        raise Exception("Test exception")

    @view_config(name="forbidden")
    def forbidden(self):
        """A view which is always forbidden"""
        raise HTTPForbidden()

    @view_config(name="not_found")
    def not_found(self):
        """A view which is not found"""
        raise HTTPNotFound()
