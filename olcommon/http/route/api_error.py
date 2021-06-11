# -*- coding:utf-8 -*-

from datetime import datetime
from pyramid.decorator import reify
from pyramid.response import Response
from pyramid.httpexceptions import HTTPClientError
from pyramid.view import view_config
from traceback import format_exception
from traceback import format_exception_only


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