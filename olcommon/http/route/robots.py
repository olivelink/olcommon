
from pyramid.view import view_config


@view_config(route_name="robots")
def robots_view(request):
    response = request.response
    registry = request.registry
    response.text = registry["templates"]["robots.txt"](
        registry=registry,
        request=request,
    )
    response.content_type = "text/plain"
    return response


def includeme(config):
    """Configures access to documentation"""
    config.add_route("robots", "robots.txt")
    config.scan(".robots")