# -*- coding: utf-8 -*-
"""Sessions and authorization configuration for pyramid"""

from .. import utils
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.interfaces import IAuthenticationPolicy
from pyramid.security import Authenticated
from pyramid.security import Everyone
from zope.interface import implementer

import logging
import secrets


logger = logging.getLogger("apweb")


def get_auth_policy_name_for_request(request):
    """Determin which policy should be used for authentication"""
    domain = request.domain
    if utils.PATTERN_API_DOMAIN.match(domain) is not None:
        return "jwt"
    return "authtkt"


@implementer(IAuthenticationPolicy)
class JWTAuthenticationPolicy(object):
    """Authentication policy for API based requests"""

    def unauthenticated_userid(self, request):
        """Extract a userid from a jwt token"""
        claims = request.jwt_claims
        if claims is None:
            return None

        # Check for the claim of an access token
        if "access" in claims.get("aud", []):
            return claims.get("sub", None)
        else:
            return None

    def authenticated_userid(self, request):
        raise NotImplementedError()

    def effective_principals(self, request, userid=None):
        raise NotImplementedError()

    def remember(self, request, userid, **kw):
        raise NotImplementedError()

    def forget(self, request):
        raise NotImplementedError()


@implementer(IAuthenticationPolicy)
class AuthenticationPolicy(object):
    """Global authentication policy"""

    def __init__(self, authtkt_policy_kwargs):
        self.jwt_policy = JWTAuthenticationPolicy()
        self.authtkt_policy = AuthTktAuthenticationPolicy(**authtkt_policy_kwargs)

    def policy(self, request):
        if request.auth_policy_name_for_request == "jwt":
            return self.jwt_policy
        elif request.auth_policy_name_for_request == "authtkt":
            return self.authtkt_policy
        else:
            raise Exception("Unknown authentication policy")

    def unauthenticated_userid(self, request):
        """Proxy unauthenticated_userid method to the auth policy for this request"""
        return self.policy(request).unauthenticated_userid(request)

    def remember(self, request, userid, **kw):
        """Proxy remember method to authtkt_policy

        Regardless of the policy being used, this method will always apply authtkt_policy

        """
        return self.authtkt_policy.remember(request, userid, **kw)

    def forget(self, request):
        """Proxy forget method to the auth policy for this request"""
        return self.policy(request).forget(request)

    def authenticated_userid(self, request):
        if request.user is not None:
            return self.unauthenticated_userid(request)
        else:
            return None

    def effective_principals(self, request):
        """Set the effective principals"""
        principals = [Everyone]
        principals.extend([f"{t}:{n}" for t, n in request.identifiers])
        principals.extend([f"group:{g}" for g in request.groups])
        principals.extend([f"role:{r}" for r in request.roles])
        return principals


def includeme(config):
    """Configure pyramid to use ACL authorization and use sessions"""
    settings = config.get_settings()
    registry = config.registry

    # method to determin which auth policy to use
    config.add_request_method(
        get_auth_policy_name_for_request, "auth_policy_name_for_request", reify=True
    )

    # Setup authtkt settings
    authtkt_secret = settings.get("authtkt_secret", None)
    if authtkt_secret is None:
        authtkt_secret = secrets.token_urlsafe(32)

    authtkt_hashalg = settings.get("authtkt_hashalg", "sha512")

    authtkt_policy_kwargs = {
        "secret": authtkt_secret,
        "secure": registry["cookie_session_secure"],
        "timeout": registry["cookie_session_timeout"],
        "reissue_time": registry["cookie_session_reissue_time"],
        "max_age": registry["cookie_session_timeout"],
        "hashalg": authtkt_hashalg,
        "http_only": True,
        "wild_domain": False,
    }

    authentication_policy = AuthenticationPolicy(authtkt_policy_kwargs)
    config.set_authentication_policy(authentication_policy)
