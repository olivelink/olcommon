from chameleon import PageTemplateLoader
from datetime import date
from datetime import datetime
from decimal import Decimal
from uuid import UUID


import os.path
import pyramid.renderers

TEMPLATE_DIR = os.path.join(dirname(__file__), "templates")


def includeme(config):
    """Configure a pyramid application
    """
    settings = config.get_settings()
    registry = config.registry

    # Configure registry
    registry["cookie_prefix"] = settings["cookie_prefix"]
    registry["cookie_domain"] = settings["cookie_domain"]
    registry["session_timeout"] = int(settings["session_timeout"])
    registry["session_secret"] = settings["session_secret"]

    # Add a template loader
    template_dirs = ( 
        [p for p in settings["template_dirs"].split() if p.strip()] +
        [TEMPLATE_DIR]
    )
    registry["templates"] = PageTemplateLoader(
        template_dirs,
        debug=registry["is_debug"],
    )

    # Add adaptors to JSON renderer
    json_renderer = pyramid.renderers.JSON()
    json_renderer.add_adapter(datetime, json_datetime_adapter)
    json_renderer.add_adapter(date, json_datetime_adapter)
    json_renderer.add_adapter(UUID, json_uuid_adapter)
    json_renderer.add_adapter(Decimal, json_decimal_adapter)
    config.add_renderer("json", json_renderer)

    # Add the jsend renderer
    config.add_renderer("jsend", JSendRenderer)

    # Includes
    config.include(".docs")


# JSON Renderer

def json_datetime_adapter(obj, request):
    """Adapt datetime to JSON"""
    return obj.isoformat()


def json_uuid_adapter(obj, request):
    return str(obj)


def json_decimal_adapter(obj, request):
    return str(obj)


class JSendRenderer(object):
    def __init__(self, info):
        pass

    def __call__(self, value, system):
        value = {"status": "success", "data": value}
        request = system.get("request", None)
        result = pyramid.renderers.render("json", value, request)
        if request:
            response = request.response
            response.content_type = "application/json"
            response.charset = "utf-8"
        return result