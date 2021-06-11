# -*- coding: utf-8 -*-

from . import policy
from pyramid.security import Authenticated
from pyramid.security import Everyone
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import patch

import unittest


class TestAuthentication(unittest.TestCase):
    @patch("apweb.utils.PATTERN_API_DOMAIN")
    def test_get_auth_policy_name_for_api(self, pattern_api_domain):
        request = MagicMock()
        pattern_api_domain.match.return_value = "foo"
        result = policy.get_auth_policy_name_for_request(request)
        self.assertEqual(result, "jwt")

    @patch("apweb.utils.PATTERN_API_DOMAIN")
    def test_get_auth_policy_name_for_non_api(self, pattern_api_domain):
        request = MagicMock()
        pattern_api_domain.match.return_value = None
        result = policy.get_auth_policy_name_for_request(request)
        self.assertEqual(result, "authtkt")


class TestJWTAuthenticationPolicy(unittest.TestCase):
    def test_unauthenticated_userid(self):
        p = policy.JWTAuthenticationPolicy()
        request = MagicMock()
        request.jwt_claims = {"sub": "foo", "aud": ["access"]}
        userid = p.unauthenticated_userid(request)
        self.assertEqual(userid, "foo")

    def test_unauthenticated_userid_without_jwt(self):
        p = policy.JWTAuthenticationPolicy()
        request = MagicMock()
        request.jwt_claims = None
        userid = p.unauthenticated_userid(request)
        self.assertIsNone(userid)

    def test_unauthenticated_userid__without_access(self):
        p = policy.JWTAuthenticationPolicy()
        request = MagicMock()
        request.jwt_claims = {"sub": "foo", "aud": ["refresh"]}
        userid = p.unauthenticated_userid(request)
        self.assertIsNone(userid)


class TestAuthenticationPolicy(unittest.TestCase):
    @patch("apweb.authentication.policy.AuthTktAuthenticationPolicy")
    def test_init(self, AuthTktAuthenticationPolicy):  # noqa: 803
        p = policy.AuthenticationPolicy({"one": 1})
        self.assertIsInstance(p.jwt_policy, policy.JWTAuthenticationPolicy)
        self.assertEqual(p.authtkt_policy, AuthTktAuthenticationPolicy.return_value)
        AuthTktAuthenticationPolicy.assert_called_with(one=1)

    def test_policy(self):
        p = policy.AuthenticationPolicy({"secret": "one"})
        request = MagicMock()

        request.auth_policy_name_for_request = "jwt"
        result = p.policy(request)
        self.assertEqual(p.jwt_policy, result)

        request.auth_policy_name_for_request = "authtkt"
        result = p.policy(request)
        self.assertEqual(p.authtkt_policy, result)

    def test_proxy_methods(self):
        p = policy.AuthenticationPolicy({"secret": "one"})
        p.policy = Mock()
        inner_policy = p.policy.return_value

        p.unauthenticated_userid("foo")
        inner_policy.unauthenticated_userid.assert_called_with("foo")

        result = p.remember("bar", "user1")
        inner_policy.remember.assert_called_with("bar", "user1")
        self.assertEqual(result, inner_policy.remember.return_value)

        result = p.forget("123")
        inner_policy.forget.assert_called_with("123")
        self.assertEqual(result, inner_policy.forget.return_value)

    def test_authenticated_userid_no_user(self):
        p = policy.AuthenticationPolicy({"secret": "one"})
        request = MagicMock()
        request.user = None
        userid = p.authenticated_userid(request)
        self.assertIsNone(userid)

    def test_authenticated_userid(self):
        p = policy.AuthenticationPolicy({"secret": "one"})
        request = MagicMock()
        p.unauthenticated_userid = MagicMock()
        expected_userid = p.unauthenticated_userid.return_value
        userid = p.authenticated_userid(request)
        p.unauthenticated_userid.assert_called_with(request)
        self.assertEqual(userid, expected_userid)

    def test_effective_principals_no_user(self):
        request = MagicMock()
        p = policy.AuthenticationPolicy({"secret": "one"})
        p.authenticated_userid = MagicMock(return_value=None)
        request.groups = ["green", "blue"]
        request.roles = ["super", "viewer"]
        result = p.effective_principals(request)
        self.assertEqual(
            result, [Everyone, "group:green", "group:blue", "role:super", "role:viewer"]
        )

    def test_effective_principals(self):
        request = MagicMock()
        p = policy.AuthenticationPolicy({"secret": "one"})
        p.authenticated_userid = MagicMock(return_value="user1")
        request.groups = ["green", "blue"]
        request.roles = ["super", "viewer"]
        result = p.effective_principals(request)
        self.assertEqual(
            result,
            [
                Everyone,
                Authenticated,
                "user:user1",
                "group:green",
                "group:blue",
                "role:super",
                "role:viewer",
            ],
        )


class TestConfigure(unittest.TestCase):
    @patch("apweb.authentication.policy.AuthenticationPolicy")
    def test_configure(self, AuthenticationPolicy):  # noqa: 803

        config = MagicMock()
        config.registry = {
            "cookie_session_secure": True,
            "cookie_session_timeout": 123,
            "cookie_session_reissue_time": 12,
        }
        config.get_settings.return_value = {"authtkt_secret": "super secret"}
        policy.includeme(config)

        config.add_request_method.assert_called_with(
            policy.get_auth_policy_name_for_request,
            "auth_policy_name_for_request",
            reify=True,
        )
        AuthenticationPolicy.assert_called_with(
            {
                "secret": "super secret",
                "secure": True,
                "timeout": 123,
                "reissue_time": 12,
                "http_only": True,
                "wild_domain": False,
            }
        )
        config.set_authentication_policy.assert_called_with(
            AuthenticationPolicy.return_value
        )
