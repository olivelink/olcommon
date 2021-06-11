# -*- coding:utf-8 -*-

from datetime import timedelta
from unittest.mock import MagicMock
from unittest.mock import patch

import apweb.authentication.jwt as apweb_jwt
import unittest


class TestRefreshTokenLoginProvider(unittest.TestCase):
    def setUp(self):
        self.provider = apweb_jwt.RefreshTokenLoginProvider()

    def test_userid_for_login_request_no_claim(self):
        request = MagicMock()
        request.jwt_claims = None
        self.assertIsNone(self.provider.userid_for_login_request(request))

    def test_userid_for_login_request_access_token(self):
        request = MagicMock()
        request.jwt_claims = {"sub": "foo", "aud": ["access"]}
        self.assertIsNone(self.provider.userid_for_login_request(request))

    def test_userid_for_login_request(self):
        request = MagicMock()
        request.jwt_claims = {"sub": "foo", "aud": ["refresh"]}
        self.assertEqual(self.provider.userid_for_login_request(request), "foo")


class TestJWT(unittest.TestCase):
    @patch("jwt.decode")
    def test_get_jwt_claims(self, jwt_decode):

        request = MagicMock()
        request.registry = {}
        request.registry["jwt_public_key"] = "pub key"
        request.registry["jwt_algorithm"] = "myalgo"
        request.registry["jwt_leeway"] = timedelta(seconds=10)
        request.authorization = ("Bearer", "mytoken")

        claims = apweb_jwt.get_jwt_claims(request)
        self.assertEqual(claims, jwt_decode.return_value)

        jwt_decode.assert_called_with(
            "mytoken",
            key="pub key",
            algorithms=["myalgo"],
            leeway=timedelta(seconds=10),
            options={"verify_aud": False},
        )

    @patch("jwt.decode")
    def test_get_jwt_claims_no_pub_key(self, jwt_decode):

        request = MagicMock()
        request.registry = {}
        request.registry["jwt_public_key"] = None
        request.registry["jwt_algorithm"] = "myalgo"
        request.registry["jwt_leeway"] = timedelta(seconds=10)
        request.authorization = ("Bearer", "mytoken")

        claims = apweb_jwt.get_jwt_claims(request)
        self.assertIsNone(claims)

    @patch("jwt.encode")
    def test_generate_jwt(self, jwt_encode):
        request = MagicMock()
        request.registry = {}
        request.registry["jwt_private_key"] = "priv key"
        request.registry["jwt_algorithm"] = "myalgo"
        request.registry["jwt_leeway"] = timedelta(seconds=10)
        token = apweb_jwt.generate_jwt(request, sub="user1")
        expected_token = jwt_encode.return_value.decode()
        self.assertEqual(token, expected_token)
        jwt_encode.assert_called_with(
            {"sub": "user1"}, key="priv key", algorithm="myalgo"
        )

    def test_generate_jwt_not_configured(self):
        request = MagicMock()
        request.registry = {}
        request.registry["jwt_private_key"] = None
        request.registry["jwt_algorithm"] = None
        with self.assertRaises(apweb_jwt.JWTNotConfiguredError):
            apweb_jwt.generate_jwt(request, sub="user1")

    @patch("apweb.authentication.jwt.RefreshTokenLoginProvider")
    def test_includeme_no_config(self, RefreshTokenLoginProvider):  # noqa: N803
        config = MagicMock()
        config.get_settings.return_value = {}
        config.registry = {}
        apweb_jwt.includeme(config)
        self.assertEqual(
            config.registry,
            {
                "jwt_private_key": None,
                "jwt_public_key": None,
                "jwt_algorithm": None,
                "jwt_leeway": timedelta(seconds=10),
                "jwt_access_ttl": timedelta(seconds=60 * 60 * 24),
                "jwt_refresh_ttl": timedelta(seconds=60 * 60 * 24 * 365),
            },
        )
        config.add_request_method.assert_any_call(
            apweb_jwt.get_jwt_claims, "jwt_claims", reify=True
        )
        config.add_request_method.assert_any_call(
            apweb_jwt.generate_jwt, "generate_jwt"
        )
        config.register_login_provider.assert_called_with(
            RefreshTokenLoginProvider.return_value
        )

    def test_includeme(self):
        config = MagicMock()
        config.get_settings.return_value = {
            "jwt_private_key": "privkey",
            "jwt_public_key": "pubkey",
            "jwt_algorithm": "rsa",
            "jwt_leeway": "20",
            "jwt_access_ttl": "30",
            "jwt_refresh_ttl": "40",
        }
        config.registry = {}
        apweb_jwt.includeme(config)
        self.assertEqual(
            config.registry,
            {
                "jwt_private_key": "privkey",
                "jwt_public_key": "pubkey",
                "jwt_algorithm": "rsa",
                "jwt_leeway": timedelta(seconds=20),
                "jwt_access_ttl": timedelta(seconds=30),
                "jwt_refresh_ttl": timedelta(seconds=40),
            },
        )
