from .security import SecurityPolicy
from chameleon import PageTemplateLoader
from datetime import date
from datetime import datetime
from datetime import timedelta
from decimal import Decimal
from jwt.exceptions import ExpiredSignatureError
from jwt.exceptions import InvalidTokenError
from uuid import UUID
from os.path import dirname

import jwt
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
    registry["docs_dist"] = settings["docs_dist"]

    # Get and check jwt keys
    registry["jwt_private_key"] = settings["jwt_private_key"]
    assert registry["jwt_private_key"].strip()
    registry["jwt_public_key"] = settings["jwt_public_key"]
    assert registry["jwt_public_key"].strip()

    # jwt options
    registry["jwt_algorithm"] = settings["jwt_algorithm"]
    registry["jwt_leeway"] = timedelta(seconds=int(settings["jwt_leeway"]))
    registry["jwt_access_ttl"] = timedelta(seconds=int(settings["jwt_access_ttl"]))
    registry["jwt_refresh_ttl"] = timedelta(seconds=int(settings["jwt_refresh_ttl"]))
    
    # Build template loader
    templates_extra_builtins = {
        "registry": registry,
    }
    registry["templates"] = PageTemplateLoader(
        (
            [p for p in settings["template_dirs"].split() if p.strip()] +
            [TEMPLATE_DIR]
        ),
        extra_builtins=templates_extra_builtins,
        registry=registry,
        auto_reload=registry["is_debug"],
    )
    templates_extra_builtins["templates"] = registry["templates"]


def configure_rendering(config):
    registry = config.registry

    config.set_security_policy(SecurityPolicy())

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
    config.add_request_method(get_jwt_claims, "jwt_claims", reify=True)
    config.add_request_method(generate_jwt, "generate_jwt")

def configure_routes(config):
    config.include(".route.robots")
    config.include(".route.check")
    config.include(".route.test")
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


def get_jwt_claims(request):
    """Return the JSON web token claim from the request object.

    Only supports public/private key pair forms of JWT and must have
    request.registry.jwt_public_key and request.registry_jwt_algorithm defined.

    A registry.jwt_leeway (timedelta) can be defined. By default it is 10 seconds

    Args:
        request: A pyramid request object

    Returns:
        dict: The claims dictionary if a verified JWT was found
        None: Indicats that there was not valid JWT token given
    """

    # Check that we have a public key
    registry = reequest.registry
    public_key = registry["jwt_public_key"]
    algorithm = registry["jwt_algorithm"]
    leeway = registry["jwt_leeway"]

    # Extract raw token
    token = None

    auth_type, auth_token = request.authorization or (None, None)
    if auth_type == "Bearer":
        token = auth_token

    if token is None:
        token = request.params.get("_jwt", None) or None

    if token is None:
        return None

    try:
        claims = jwt.decode(
            token,
            key=public_key,
            algorithms=[algorithm],
            leeway=leeway,
            options={"verify_aud": False},
        )  # we verify the aud claim in the security policy
    except ExpiredSignatureError:
        claims = None
    except InvalidTokenError as e:
        claims = None

    return claims


def generate_jwt(request, **claims):
    """Generate a JSON Web Token (JWT) with the given claims.

    THe token generated contains the claims signed with request.registry.private_key
    using the algorithm request.registry.algorithm

    Returns:
        str: The encoded and signed json web token
    """
    private_key = request.registry["jwt_private_key"]
    algorithm = request.registry["jwt_algorithm"]
    if private_key is None or algorithm is None:
        raise JWTNotConfiguredError()
    token = jwt.encode(claims, key=private_key, algorithm=algorithm)
    # Newer versions of jwt module return strings instead of bytes
    return token.decode() if isinstance(token, bytes) else token

# JSON Renderer

def json_datetime_adapter(obj, request):
    """Adapt datetime to JSON"""
    return obj.isoformat()


def json_uuid_adapter(obj, request):
    return str(obj)


def json_decimal_adapter(obj, request):
    return str(obj)


class JSendRenderer:
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