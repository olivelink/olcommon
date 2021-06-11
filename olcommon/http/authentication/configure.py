# -*- coding:utf-8 -*-


def get_user(request):
    return None


def get_identifiers(request):
    userid = request.authenticated_userid
    if userid:
        return [("user", userid)]
    return []


def get_groups(request):
    return []


def get_roles(request):
    return []


def should_check_csrf(request):
    """Determine if the csrf token should be checked"""
    return request.auth_policy_name_for_request != "jwt"


def includeme(config):
    config.include(".jwt")
    config.include(".policy")

    # setup csrf
    config.set_default_csrf_options(callback=should_check_csrf)

    # Setup default request methods
    config.add_request_method(get_user, "user", reify=True)
    config.add_request_method(get_identifiers, "identifiers", reify=True)
    config.add_request_method(get_groups, "groups", reify=True)
    config.add_request_method(get_roles, "roles", reify=True)
