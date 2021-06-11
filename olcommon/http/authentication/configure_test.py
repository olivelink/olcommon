# -*- coding:utf-8 -*-
from . import configure
from unittest.mock import MagicMock

import unittest


class TestConfigure(unittest.TestCase):
    def test_default_methods(self):
        self.assertEqual(configure.get_user(None), None)
        self.assertEqual(configure.get_groups(None), [])
        self.assertEqual(configure.get_roles(None), [])

    def test_should_check_csrf(self):

        request = MagicMock()
        request.auth_policy_name_for_request = "authtkt"
        self.assertTrue(
            configure.should_check_csrf(request),
            "expected to check csrf for authtkt authentication",
        )

        request = MagicMock()
        request.auth_policy_name_for_request = "jwt"
        self.assertFalse(
            configure.should_check_csrf(request),
            "expected not to check csrf for jwt authentication",
        )

    def test_includeme(self):
        config = MagicMock()

        configure.includeme(config)
        config.include.assert_any_call(".jwt")
        config.include.assert_any_call(".policy")
        config.set_default_csrf_options.assert_any_call(
            callback=configure.should_check_csrf
        )
        config.add_request_method.assert_any_call(
            configure.get_groups, "groups", reify=True
        )
        config.add_request_method.assert_any_call(
            configure.get_roles, "roles", reify=True
        )
