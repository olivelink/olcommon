# -*- coding:utf-8 -*-

from olcommon.utils import PATTERN_API_DOMAIN
from datetime import datetime
from pyramid.decorator import reify
from pyramid.response import Response
from pyramid.httpexceptions import HTTPClientError
from pyramid.view import view_config
from traceback import format_exception
from traceback import format_exception_only

import pyramid.events


DEFAULT_CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST,PATCH,GET,DELETE,PUT,OPTIONS",
    "Access-Control-Allow-Headers": "Origin, Content-Type, Accept, Authorization, Client-Version",
    "Access-Control-Allow-Credentials": "true",
    "Access-Control-Max-Age": "3600",
}


def add_headers(request, response):
    """Add CORS headers to a response object"""

    headers = {**DEFAULT_CORS_HEADERS}

    # Get
    origin = request.headers.get("origin", "*")
    headers["Access-Control-Allow-Origin"] = origin

    # Set vary header
    vary = response.headers.get("vary", '')
    if vary:
        vary = vary + ', Origin'
    else:
        vary = 'Origin'
    headers['Vary'] = vary
    
    response.headers.update(headers)


def new_request_handler(event):
    """Handle the new request event adding a CORS add_headers responses for particular domais

    Adds headers to domains starting with "api."
    """
    request = event.request
    if PATTERN_API_DOMAIN.match(request.domain):
        request.add_response_callback(add_headers)


@view_config(route_name="api_options")
def preflight(context, request):
    """A pyramid view to handle OPTIONS request for preflight checks of CROS"""
    # the add_headers callback will add appropreate cors headers to the
    return request.response



@view_config(route_name="api", context=Exception, renderer="json")
class HandleException(object):
    """Handle and exception and return a json object in the jsend message spec format"""

    def __init__(self, context, request):
        self.context = context
        self.request = request

    status = "error"
    default_message = "Server Error"

    @reify
    def timestamp(self):
        return datetime.utcnow().isoformat()

    @reify
    def message(self):
        context_message = getattr(self.context, "jsend_message", None)
        if context_message:
            message = context_message
        elif self.code == 404:
            message = "Not found"
        elif self.code == 403:
            message = "Forbidden"
        else:
            message = None
        return message

    @reify
    def code(self):
        if isinstance(self.context, Response):
            return getattr(self.context, "code", None) or 500
        else:
            return 500

    @reify
    def exception(self):
        if self.request.exc_info:
            etype, value = self.request.exc_info[:2]
            return format_exception_only(etype, value)
        else:
            return None

    @reify
    def traceback(self):
        if self.request.exc_info:
            etype, value, tb = self.request.exc_info
            return format_exception(etype, value, tb)
        else:
            return None

    @reify
    def data(self):
        return getattr(self.context, "jsend_data", None)

    def __call__(self):
        self.request.response.status_code = self.code
        jsend = {
            "timestamp": self.timestamp,
            "status": self.status,
            "data": self.data,
            "message": self.message or self.default_message,
            "code": self.code,
        }
        if "role:system-owner" in self.request.effective_principals:
            jsend["exception"] = self.exception
            jsend["traceback"] = self.traceback

        return jsend


@view_config(route_name="api", context=HTTPClientError, renderer="json")
class HandleClientError(HandleException):
    """Handle a client error and return a json object in the jsend message spec format"""

    status = "fail"
    default_message = "Client error"
    
    @reify
    def message(self):
        """Allow backing down to the execption message passing through"""
        super_message = super().message
        if super_message:
            return super_message
        
        # Construct message
        parts = []
        title = getattr(self.context, 'title', None)
        if title:
            parts.append(title)
        message = getattr(self.context, 'message', None)
        if message:
            parts.append(message)
        if len(parts) > 0:
            return ': '.join(parts)

        return None


def includeme(config):
    config.add_route("api_options", "/api/*path", request_method="OPTIONS")
    config.add_subscriber(new_request_handler, pyramid.events.NewRequest)
    config.add_route("api", "/api/v1/*traverse")
    config.scan(".api")