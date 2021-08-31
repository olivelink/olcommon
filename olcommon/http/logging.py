from pyramid.response import Response
from datetime import timedelta
from datetime import datetime

import logging
import sys



logger_access = logging.getLogger("access")


def logger_handler_tween_factory(handler, registry):

    def logger_handler_tween(request):

        # Perform request
        response = None
        exception_raised = False
        timestamp_start = datetime.now()
        try:
            # Perform request
            response = handler(request)
        except Exception as err:
            # If there is an error then
            response = err
            exception_raised = True
        timestamp_end = datetime.now()
        latency =  timestamp_end - timestamp_start
        if latency < timedelta():
            latency = timedelta()
        latency = latency.total_seconds()

        # Do logging
        log(request, response, exception_raised, latency)

        # Raise or return
        if exception_raised:
            raise response
        else:
            return response

    return logger_handler_tween


def log(request, response, exception_raised, latency):
    registry = request.registry

    # Do logging
    try:
        route = getattr(request, "matched_route")
        route_name = (route and route.name) or ""
        view_name = getattr(request, "view_name", "")

        if isinstance(response, Response):
            response_status = response.status_code
            response_content_length = response.content_length
            exc_info = getattr(request, "exc_info")
        else:
            if exception_raised:
                response_status = 500
                response_content_length = None
                exc_info = sys.exc_info()
            else:
                raise Exception("Unexpected response or exception from handler.")
        
        # Calculate values
        
        actor = request.unauthenticated_userid
        actor_ip = request.client_addr
        message = (
            f'"{request.method} {request.url}"'
            f" {response_status} {response_content_length}"
            f' "{request.referer or ""}" "{request.user_agent or ""}"'
            f' ({route_name}/{view_name})'
            f' {latency:0.6f}s'
        )
        extra = extra={
            "actor": actor,
            "actor_ip": actor_ip,
            "actor_formatted": f'{actor_ip or "-"} {actor or "-"}',
            "request_method": request.method,
            "request_url": request.url,
            "response_status": response_status,
            "response_content_length": response_content_length,
            "user_agent": request.user_agent,
            "referer": request.referer,
            "route_name": route_name,
            "view_name": view_name,
            "latency": latency,                
        }

        # Select level
        if route_name == "check" and view_name == "app":  # Don't log app alive requests
            emit =logger_access.debug
        elif 500 <= int(response_status) < 600:
            emit = logger_access.error
        elif 400 <= int(response_status) < 500:
            emit = logger_access.info
        elif exc_info:
            emit = logger_access.error
        else:
            emit = logger_access.info

        # Emit
        emit(message, exc_info=exc_info, extra=extra)

    except:
        registry["logger"].exception("An error occured whilst logging to the access logger.")
        raise
