# -*- coding:utf-8 -*-

from .. import utils
from pyramid.view import view_config


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
    if utils.PATTERN_API_DOMAIN.match(request.domain):
        request.add_response_callback(add_headers)


@view_config(route_name="api_options")
def preflight(context, request):
    """A pyramid view to handle OPTIONS request for preflight checks of CROS"""
    # the add_headers callback will add appropreate cors headers to the
    return request.response
