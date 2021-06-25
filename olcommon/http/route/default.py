from pyramid.view import exception_view_config
from pyramid.view import forbidden_view_config
from pyramid.view import notfound_view_config

import pyramid.httpexceptions


@exception_view_config()
@notfound_view_config()
@forbidden_view_config()
def error(context, request):
    """Generic error handeling"""
    response = request.response
    if isinstance(context, pyramid.httpexceptions.HTTPException):
        response.status_code = context.code
    else:
        response.status_code = 500

    response.text = request.registry["templates"]["error.pt"](
        response=response,
        request=request,
    )
    return response


def includeme(config):

    if not config.registry['is_debug']:
        config.scan('.default')