from . import default
from pyramid.view import exception_view_config
from pyramid.view import forbidden_view_config
from pyramid.view import notfound_view_config
from pyramid.view import view_config
from pyramid.view import view_defaults
from pyramid.exceptions import HTTPForbidden
from pyramid.exceptions import HTTPNotFound


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


@exception_view_config(route_name="test")
@notfound_view_config(route_name="test")
@forbidden_view_config(route_name="test")
def error(context, request):
    """Allow for rendering the errors on develop but just in the test route"""
    return default.error(context, request)


def includeme(config):
    config.add_route("test", "_test/*traverse")
    config.scan(".test")