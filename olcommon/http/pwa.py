from pyramid.response import FileResponse
from pyramid.response import Response
import os.path


def add_pwa(config, path, name, file="index.html", *args, **kwargs):
    """Configure a progressive web app on a route"""
    add_pwa_resource(config, path, name)
    add_pwa_view(config, path, name, file, *args, **kwargs)


def add_pwa_resource(config, path, name):
    registry = config.registry

    # expose the assets
    static_view_name = f"++{name}++"
    config.add_static_view(
        static_view_name,
        path,
        cache_max_age=5 if registry["is_debug"] else 600,
    )


def add_pwa_view(config, path, name, html_file="index.html", *args, **kwargs):
    registry = config.registry

    # Add html route
    config.add_route(name, *args, **kwargs)

    # Construct html view
    html_path = os.path.join(path, html_file)

    # Use a view that reads the disk on each request if we
    # are in debug mode
    if registry["is_debug"]:
        def serve_pwa(request):
            """Serve up the supplypredict html application"""
            debug_response = FileResponse(
                html_path,
                cache_max_age=0,
                content_type="text/html",
            )
            return debug_response

        pwa_http_cache = 0

    # Read from the disk immidatly and returen the same
    # response every time.
    else:
        with open(html_path) as fin:
            html_body = fin.read()

        def serve_pwa(request):
            return Response(
                body=html_body,
                content_type="text/html",
            )
            return response
        
        pwa_http_cache = 600
    
    config.add_view(serve_pwa, route_name=name, request_method="GET", http_cache=pwa_http_cache)