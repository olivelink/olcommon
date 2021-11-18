from ctq import ResourceCache
from pyramid.authorization import Everyone

import logging
import pyramid_mailer
import zope.sqlalchemy
import transaction as zope_transaction
import transaction.interfaces as zope_transaction_interfaces

class SiteBase(object):
    """A primitive site"""
    
    user_email_store_lower_case = True

    def __init__(self, *args, registry, transaction, db_session, redis, mailer, get_logger, **kwargs):
        super().__init__(*args, **kwargs)
        self.registry = registry
        self.mailer = mailer
        self.transaction = transaction
        self.db_session = db_session
        self.redis = redis
        self.get_logger = get_logger

    def init_transaction(self):
        try:
            tx = self.transaction.get()
        except zope_transaction_interfaces.NoTransaction:
            self.transaction.begin()
            tx = self.transaction.get()

        before_commit_hooks = (h[0] for h in tx.getBeforeCommitHooks())
        if self.on_before_commit not in before_commit_hooks:
            tx.addBeforeCommitHook(self.on_before_commit)

        after_commit_hooks = (h[0] for h in tx.getAfterCommitHooks())
        if self.on_after_commit not in after_commit_hooks:
            tx.addAfterCommitHook(self.on_after_commit)

        after_abort_hooks = (h[0] for h in tx.getAfterAbortHooks())
        if self.on_after_abort_hook not in after_abort_hooks:
            tx.addAfterAbortHook(self.on_after_abort_hook)

        self.transaction.begin = lambda: tx  # Neuter the begin method.

    def on_before_commit(self):
        return

    def on_after_commit(self, success):
        return

    def on_after_abort_hook(self):
        # Close down this resource tree from furuther use.
        self.transaction = None
        self.redis = None
        if isinstance(self, ResourceCache):
            self.resource_cache_clear()

    @classmethod
    def from_registry(cls, registry, *args, **kwargs):
        tm = zope_transaction.TransactionManager(explicit=True)
        db_session = registry["null_pool_db_session_factory"]()
        zope.sqlalchemy.register(db_session, transaction_manager=tm, keep_session=True)

        class MailerTmp(pyramid_mailer.Mailer):
            def __init__(self, **kw):
                super().__init__(transaction_manager=tm, **kw)

        if registry["use_debug_mailer"]:
            mailer = pyramid_mailer.mailer.DebugMailer('mail')  # Store mail in 'mail' dir in CWD
        else:
            mailer = pyramid_mailer.Mailer(
                transaction_manager=tm, smtp_mailer=registry["sendgrid_smtp_mailer"]
            )

        site = cls(**{
            "registry": registry,
            "transaction": tm,
            "db_session": db_session,
            "redis": registry["get_redis"](),
            "mailer": mailer,
            "get_logger": registry["get_logger"],
            **kwargs,
        })
        site.init_transaction()
        return site

    @classmethod
    def from_request(cls, request, **kwargs):
        """Create a site object from a request object"""
        site = cls(**{
            'registry': request.registry,
            'db_session': request.db_session,
            'redis': request.redis,
            'mailer': request.mailer,
            'transaction': request.tm,
            "get_logger": request.get_logger,
            **kwargs,
        })
        site.init_transaction()
        return site

    def get_user_for_identity(self, identity):
        return None

    def get_principals(self, identity, user):
        return [Everyone]

    @property
    def application_url(self):
        return self.registry["application_url"]

    @property
    def application_id(self):
        return self.registry["application_id"]
