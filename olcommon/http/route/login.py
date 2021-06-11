# -*- coding:utf-8 -*-

from ..authentication.jwt import JWTNotConfiguredError
from ..login import ILoginProvider
from datetime import datetime
from pyramid.decorator import reify
from pyramid.httpexceptions import HTTPForbidden
from pyramid.httpexceptions import HTTPFound
from pyramid.view import view_config
from uuid import uuid4

import logging
import pyramid.security


logger = logging.getLogger("apweb.view.login")


class NotAbleToCreateLogin(Exception):
    """Was not able to create a login"""


class LoginView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

    @reify
    def userid(self):
        for provider in self.request.registry.getAllUtilitiesRegisteredFor(
            ILoginProvider
        ):
            userid = provider.userid_for_login_request(self.request)
            if userid:
                return userid
        return self.request.authenticated_userid

    @reify
    def device_id(self):
        return uuid4().hex

    @reify
    def jwt_iat(self):
        """datetime: The JWT iat (issued at) claism"""
        return datetime.utcnow()

    @reify
    def jwt_access_exp(self):
        """datetime: The JWT exp (expiry) claism for the access token"""
        return self.jwt_iat + self.request.registry["jwt_access_ttl"]

    @reify
    def jwt_access_token(self):
        """str: A newly JWT access toekn"""
        return self.request.generate_jwt(
            sub=self.userid,
            aud=["access"],
            iat=self.jwt_iat,
            exp=self.jwt_access_exp,
            device_id=self.device_id,
        )

    @reify
    def jwt_refresh_exp(self):
        """datetime: The JWT exp (expiry) claism for the refresh token"""
        return self.jwt_iat + self.request.registry["jwt_refresh_ttl"]

    @reify
    def jwt_refresh_token(self):
        """str: A newly JWT refresh toekn"""
        return self.request.generate_jwt(
            sub=self.userid,
            aud=["refresh"],
            iat=self.jwt_iat,
            exp=self.jwt_refresh_exp,
            device_id=self.device_id,
        )

    @view_config(
        route_name="api", name="login", request_method="POST", renderer="jsend"
    )
    def login(self):

        # Only POST requests are supported
        if self.request.method.lower() != "post":
            raise HTTPForbidden("Request method not allowed")

        # If no userid then have failed to login
        if not self.userid:
            logger.warning(
                f"Failed login attempt.\n"
                f"\tclient_addr: {self.request.client_addr}\n"
                f"\tremote_addr: {self.request.remote_addr}\n"
                f"\turl: {self.request.url}"
            )
            raise HTTPForbidden("Was not able to login")

        # Get AuthTKT cookie headers
        browser_headers = pyramid.security.remember(
            self.request, self.userid, tokens=[f"device_id-{self.device_id}"]
        )

        # Add AuthTKT cookies to response's headers
        self.request.response.headers.update(browser_headers)

        # JWT creation may fail if algorithm not set
        try:
            jwt = self.jwt_access_token
            jwt_refresh = self.jwt_refresh_token
        except NotImplementedError:
            jwt = None
            jwt_refresh = None

        # Return both JWT and AuthTKT headers so client can easily make use of either
        return {
            "jwt": jwt,
            "jwt_refresh": jwt_refresh,
            "browser_headers": browser_headers,
        }

    @view_config(
        route_name="api", name="logout", renderer="jsend"
    )
    def api_logout(self):
        self.request.session.invalidate()
        browser_headers = pyramid.security.forget(self.request)
        self.request.response.headers.extend(browser_headers)
        self.request.session.invalidate()
        return {}

    @view_config(name="logout")
    def logout(self):
        response = HTTPFound('/')
        self.request.response = response
        self.api_logout()
        return response
