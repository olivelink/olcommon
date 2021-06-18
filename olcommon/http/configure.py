from chameleon import PageTemplateLoader
from datetime import date
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from os.path import dirname

import os
import os.path
import pyramid.renderers
import zope.sqlalchemy


TEMPLATE_DIR = os.path.join(dirname(__file__), "templates")


def includeme(config):
    """Configure a pyramid application
    """
    configure_registry(config)
    configure_plugins(config)
    configure_rendering(config)
    configure_request(config)
    configure_routes(config)


def configure_plugins(config):
    registry = config.registry
    config.include("pyramid_exclog")
    config.add_settings({"tm.manager_hook": "pyramid_tm.explicit_manager"})
    config.include("pyramid_tm")
    if registry["is_debug"]:
        config.include("pyramid_debugtoolbar")
        config.include('pyramid_mailer.debug')
    else:
        config.include("pyramid_mailer")


def configure_registry(config):
    # Configure registry
    settings = config.get_settings()
    registry = config.registry
    registry["cookie_prefix"] = settings["cookie_prefix"]
    registry["cookie_domain"] = settings["cookie_domain"]
    registry["session_timeout"] = int(settings["session_timeout"])
    registry["session_secret"] = settings["session_secret"]
    registry["docs_dist"] = settings["docs_dist"]
    registry["templates"] = PageTemplateLoader(
        (
            [p for p in settings["template_dirs"].split() if p.strip()] +
            [TEMPLATE_DIR]
        ),
        registry=registry,
        auto_reload=registry["is_debug"],
    )


def configure_rendering(config):
    registry = config.registry

    # Add adaptors to JSON renderer
    json_renderer = pyramid.renderers.JSON()
    json_renderer.add_adapter(datetime, json_datetime_adapter)
    json_renderer.add_adapter(date, json_datetime_adapter)
    json_renderer.add_adapter(UUID, json_uuid_adapter)
    json_renderer.add_adapter(Decimal, json_decimal_adapter)
    config.add_renderer("json", json_renderer)

    # Add the jsend renderer
    config.add_renderer("jsend", JSendRenderer)



def configure_request(config):
    registry = config.registry

    config.set_root_factory(root_factory)
    config.add_request_method(db_session_from_request, "db_session", reify=True)
    config.add_request_method(redis_from_request, "redis", reify=True)



def configure_routes(config):
    config.include(".route.robots")
    config.include(".route.check")
    config.include(".route.docs")

# Request configuration

def root_factory(request):
    return request.registry["root_class"].from_request(request)


def db_session_from_request(request):
    """Create a dbsession for a given request"""
    db_session_factory = request.registry["db_session_factory"]
    db_session = db_session_factory()
    zope.sqlalchemy.register(db_session, transaction_manager=request.tm)
    return db_session


def redis_from_request(request):
    return request.registry["redis"]

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