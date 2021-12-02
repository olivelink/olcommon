from ..logging import ActorLoggerAdapter
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
from pprint import pprint
from pyramid.view import render_view_to_response


import jwt
import os
import os.path
import pyramid.renderers
import pyramid_mailer
import pyramid_session_redis
import zope.sqlalchemy
import logging


TEMPLATE_DIR = os.path.join(dirname(__file__), "templates")


def includeme(config):
    """Configure a pyramid application
    """
    configure_registry(config)
    configure_plugins(config)
    configure_rendering(config)
    configure_request(config)
    configure_session(config)
    configure_routes(config)


def configure_plugins(config):
    registry = config.registry
    config.add_settings({"tm.manager_hook": "pyramid_tm.explicit_manager"})
    config.include("pyramid_tm")
    if registry["is_debug"]:
        config.include("pyramid_debugtoolbar")
        config.add_settings({"pyramid.reload_templates": "true"})
    config.include("pyramid_chameleon")

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

    config.add_subscriber(inject_template_vars, pyramid.events.BeforeRender)

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
    config.add_request_method(get_logger, "get_logger")
    config.add_request_method(site_factory, "site", reify=True)
    config.set_root_factory(root_factory)
    config.add_request_method(get_user, "user", reify=True)
    config.add_request_method(get_principals, "principals", reify=True)
    config.add_request_method(db_session_from_request, "db_session", reify=True)
    config.add_request_method(redis_from_request, "redis", reify=True)
    config.add_request_method(get_jwt_claims, "jwt_claims", reify=True)
    config.add_request_method(generate_jwt, "generate_jwt")
    config.set_security_policy(SecurityPolicy())
    config.add_request_method(mailer_from_reequest, "mailer", reify=True)
    config.add_tween(
        "olcommon.http.logging.logger_handler_tween_factory",
        over=[
            'pyramid.tweens.EXCVIEW',
            'pyramid_tm.tm_tween_factory',
        ],
    )


def configure_session(config):
    registry = config.registry
    settings = config.get_settings()
    secret = settings["session_secret"]
    secret = secret[:32]
    session_factory = pyramid_session_redis.RedisSessionFactory(
        secret,
        timeout=1200,  # 20 minutes
        cookie_name=registry["application_id"] + "-sid",
        cookie_domain=settings.get("cookie_domain") or None,
        cookie_max_age=1200,
        cookie_secure=not registry["is_debug"],
        cookie_httponly=True,
        client_callable=lambda request, **kwargs: request.redis,
    )
    config.set_session_factory(session_factory)


def configure_routes(config):
    config.include(".route.robots")
    config.include(".route.check")
    config.include(".route.test")
    config.include(".route.docs")
    config.include(".route.default")
    config.include(".route.api")

# Request configuration

def get_logger(request, name=None):
    name = name or request.registry["logger_name"]
    inner_logger = logging.getLogger(name)
    return ActorLoggerAdapter(inner_logger, {
        "request": request,
    })

def site_factory(request):
    return request.registry["root_class"].from_request(request)


def root_factory(request):
    return request.site


def get_user(request):
    if identity := request.identity:
        return request.site.get_user_for_identity(identity)
    return None


def get_principals(request):
    return request.site.get_principals(request.identity, request.user)



def db_session_from_request(request):
    """Create a dbsession for a given request"""
    db_session_factory = request.registry["db_session_factory"]
    db_session = db_session_factory()
    zope.sqlalchemy.register(db_session, transaction_manager=request.tm)
    return db_session

def mailer_from_reequest(request):
    if request.registry["use_debug_mailer"]:
        return pyramid_mailer.mailer.DebugMailer('mail')  # Store mail in 'mail' dir in CWD
    else:
        return pyramid_mailer.Mailer(
            transaction_manager=request.tm, smtp_mailer=request.registry["sendgrid_smtp_mailer"]
        )

def redis_from_request(request):
    return request.registry["get_redis"]()

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
    registry = request.registry
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


# Render globals

def inject_template_vars(renderer_globals):
    if renderer_globals.get("request", None) is not None:
        renderer_globals["templates"] = renderer_globals["request"].registry["templates"]
    renderer_globals["pprint"] = pprint
    renderer_globals["render_view_to_response"] = render_view_to_response


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
