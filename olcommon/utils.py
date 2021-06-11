# -*- coding:utf-8 -*-

from numbers import Number
from pyramid.decorator import reify

import re
import urllib.parse


PATTERN_API_DOMAIN = re.compile(
    r"^api\.|^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$"
)


_MISSING = object()


def normalize_query_string(query_string, ignore_prefixes=[]):
    """Normalize a query string by sorting it's key value pairs, also optionally
    filtering out key's which are prefixed by any values in ignore prefixes

    Args:
        query_string(str): A query string
        ignore_prefixes(list): A list of prefixes which should be discarded

    Returns:
        str: A normalized query string
    """
    query_string = query_string or ""
    query_items = urllib.parse.parse_qsl(query_string, keep_blank_values=True)
    filtered_query_items = []
    for key, value in query_items:
        keep = True
        for ignored_prefix in ignore_prefixes:
            if key.startswith(ignored_prefix):
                keep = False
                break
        if keep:
            filtered_query_items.append((key, value))
    query_items = sorted(filtered_query_items)
    query_string = urllib.parse.urlencode(query_items)
    return query_string


def normalize_email(email, lower_case=True):
    """Return an eamil addres that has been normalized"""
    email = email.strip()
    if lower_case:
        email = email.lower()
    return email


def yesish(value, default=None):
    """Determins if a value is yes"""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, Number):
        return bool(value)
    if isinstance(value, str):
        value = value.strip().lower()
        if value in ("", "null", "none"):
            return default
        if value in ("y", "yes", "t", "true", "1"):
            return True
        if value in ("n", "no", "f", "false", "0"):
            return False
        raise TypeError("Can not determin a yesish value")
    raise TypeError("Can not determin a yesish value")


def context_reify(name, default=_MISSING):
    """A read only context property proxy for pyramid views

    Example::
        class Obj(...):
            foo = context_propery('foo')
    """

    @reify
    def prop(self):
        value = getattr(self.context, name, default)
        if value is _MISSING:
            raise AttributeError(name)
        return value

    return prop


def map_context_reify(*names):
    """Map a set of reify property attributes into a class definition
    for which the return value is the attribue from the context
    """
    def wrapper(klass):
        for name in names:
            setattr(klass, name, context_reify(name))
        return klass
    return wrapper
