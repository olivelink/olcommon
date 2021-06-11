# -*- coding:utf-8 -*-

from . import orm
from . import user
from .utils import settings_property
from apweb.utils import normalize_query_string
from apweb.utils import yesish
from contextplus import resource

import contextplus
import pyramid_mailer
import redis
import sqlalchemy
import sqlalchemy.pool
import transaction
import zope.sqlalchemy


class Site(contextplus.Site):
    """A primitive site"""
    
    user_email_store_lower_case = True

    def __init__(self, *args, mailer=None, transaction_manager=None, request=None, is_debug=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.mailer = mailer
        self.transaction_manager = transaction_manager
        self.is_debug = is_debug
        self.is_develop = is_debug  # legacy key to be removed
        self._request = request

    @classmethod
    def from_settings(cls, settings, **kwargs):
        """Create a site object from a dictionary of settings
        """

        tm = transaction.TransactionManager(explicit=True)
        db_session = None
        redis_instance = None
        is_debug = yesish(settings.get('is_debug', settings.get('is_develop', False)))

        if settings.get("sqlalchemy.url"):
            sqlalchemy_url = settings['sqlalchemy.url']
            # Get SQLAlchemy engine
            # We need to use the NullPool if the user of this object wants to us os.fork()
            db_engine = sqlalchemy.create_engine(sqlalchemy_url, poolclass=sqlalchemy.pool.NullPool)
            db_session_factory = sqlalchemy.orm.sessionmaker()
            db_session_factory.configure(bind=db_engine)
            db_session = db_session_factory()
            zope.sqlalchemy.register(db_session, transaction_manager=tm, keep_session=True)

        if settings.get("redis_url"):
            redis_instance = redis.StrictRedis.from_url(
                settings["redis_url"], decode_responses=False
            )

        class MailerTmp(pyramid_mailer.Mailer):
            def __init__(self, **kw):
                super().__init__(transaction_manager=tm, **kw)

        if is_debug:
            mailer = pyramid_mailer.mailer.DebugMailer('mail')  # Store mail in 'mail' dir in CWD
        else:
            mailer = MailerTmp.from_settings(settings, "mail.")

        # remake kwargs allowing the user to override any values
        kwargs = {
            'settings': settings,
            'db_session': db_session,
            'redis': redis_instance,
            'mailer': mailer,
            'transaction_manager': tm,
            'is_debug': is_debug,
            **kwargs,
        }
        return cls(**kwargs)

    @classmethod
    def from_request(cls, request, **kwargs):
        """Create a site object from a request object"""
        kwargs = {
            'settings': request.registry.settings,
            'db_session': request.db_session,
            'redis': request.redis,
            'mailer': request.mailer,
            'transaction_manager': request.tm,
            'request': request,
            'is_debug': request.registry["is_debug"],
            **kwargs,
        }
        return cls(**kwargs)

    motd = None
    application_url = settings_property("application_url")
    application_deployment = settings_property("application_deployment")
    application_source_commit = settings_property("source_commit")

    @resource("users")
    def get_user_collection(self):
        return user.UserCollection(parent=self, name="users")

    def get_current_user(self):
        if self._request is not None:
            return self._request.user

    def set_redirect(self, path, query_string, redirect):
        """Set a redirect for a given url.

        The query string is re-ordered to be alphebetical. UTM paramitors are striped.

        Args:
            path (str): The path to match for a redirecting request
            query_string (str): The query string to match for a redirecting request
        """
        query_string = query_string or ""
        assert f"{path}?{query_string}".strip("?") != redirect.strip("?")
        query_string = normalize_query_string(query_string, ignore_prefixes=["utm_"])
        assert f"{path}?{query_string}".strip("?") != redirect.strip("?")
        redirect = orm.Redirect(
            request_path=path, request_query_string=query_string, redirect_to=redirect
        )
        self.db_session.merge(redirect)

    def get_redirect(self, path, query_string):
        """Retreive a redirect for a given path and query string

        Args:
            path (str): The path to match for a redirecting request
            query_string (str): The query string to match for a redirecting request
        """
        query_string = normalize_query_string(query_string, ignore_prefixes=["utm_"])
        redirects = (
            self.db_session.query(orm.Redirect)
            .filter_by(request_path=path)
            .filter(
                sqlalchemy.sql.expression.text(
                    ":input_query_string LIKE (request_query_string || '%')"
                ).bindparams(input_query_string=query_string)
            )
        )

        redirects = sorted(
            redirects, key=lambda r: len(r.request_query_string) * -1
        )  # longest query string match first
        if len(redirects) > 0:
            return redirects[0].redirect_to
        else:
            return None

    def list_redirects(self):
        """Return a list of current redirects"""
        return self.db_session.query(orm.Redirect)
