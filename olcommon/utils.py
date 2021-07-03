# -*- coding:utf-8 -*-

from numbers import Number
from pyramid.decorator import reify
from contextlib import contextmanager
from ctq import acquire
from datetime import datetime
from datetime import timedelta

import bcrypt
import ctq_sqlalchemy
import re
import secrets
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

@contextmanager
def root_context(registry):
    root = registry["root_class"].from_registry(registry)
    root.transaction.begin()
    try:
        yield root
        root.transaction.commit()
    finally:
        root.transaction.rollback()

# Recommended naming convention used by Alembic, as various different database
# providers will autogenerate vastly different names making migrations more
# difficult. See: http://alembic.zzzcomputing.com/en/latest/naming.html
ORM_NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}



class RecordExtras(ctq_sqlalchemy.RecordExtras):
    """Add extra helpers to a record class from SQLAlchemy to work
    well with the resource tree.
    """

    @property
    def registry(self):
        """SQLAlchemy defins a regitry which we don't use
        """
        return acquire(self.__parent__).registry

class UserPasswordBaseInvalidTokenError(Exception):
    """The provided token was invalid."""

class UserPasswordBase:
    """Base recipie for a user object to implmenet user password.

    The resulting object mustimplmenet the fllowing settable attributes:

    - password_hash (bytes)
    - password_reset_token (string)
    - password_reset_expiry (datetime)

    """

    PASSWORD_RESET_TOKEN_SIZE = 24

    @classmethod
    def hash_password(cls, password):
        return bcrypt.hashpw(password.encode("utf8"), bcrypt.gensalt())

    def set_password(self, password):
        password_hash = self.hash_password(password)
        self.password_hash = password_hash

    def set_password_with_token(self, password, token, now=None):
        if not self.password_reset_token:
            raise UserPasswordBaseInvalidTokenError()
        now = now or datetime.utcnow()
        if now > self.password_reset_expiry:
            raise UserPasswordBaseInvalidTokenError()
        if len(token) != self.PASSWORD_RESET_TOKEN_SIZE:
            raise UserPasswordBaseInvalidTokenError()
        if token != self.password_reset_token:
            raise UserPasswordBaseInvalidTokenError()
        self.set_password(password)
        self.password_reset_token = None
        self.password_reset_expiry = None     

    def check_password(self, password):
        if not password:
            return False
        if not self.password_hash:
            return False
        return bcrypt.checkpw(password.encode("utf8"), self.password_hash)

    def initiate_password_reset(self):
        """Generates and sets the password_reset_token and
        password_reset_expiry fields, if a password reset is not yet in
        progress or has already expired.
        """
        now = datetime.utcnow()
        token = secrets.token_urlsafe(self.PASSWORD_RESET_TOKEN_SIZE)
        self.password_reset_token = token
        self.password_reset_expiry = now + timedelta(days=1)