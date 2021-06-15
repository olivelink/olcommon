from pyramid.response import FileResponse
import os.path

def add_pwa(config, path, name, *args, **kwargs):
    """Configure a progressive web app on a route"""
    registry = config.registry

    # expose the assets
    static_view_name = f"++{name}++"
    config.add_static_view(
        static_view_name,
        path,
        cache_max_age=5 if registry["is_debug"] else 600,
    )

    # Add html route
    config.add_route(name, *args, **kwargs)

    # Construct html view
    html_path = os.path.join(path, "index.html")

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

    # Read from the disk immidatly and returen the same
    # response every time.
    else:
        response = FileResponse(
            html_path,
            cache_max_age=600,
            content_type="text/html",
        )

        def serve_pwa(request):
            return response
    
    config.add_view(serve_pwa, route_name=name, request_method="GET")