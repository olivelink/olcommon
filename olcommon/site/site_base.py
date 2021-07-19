import pyramid_mailer
import zope.sqlalchemy
import transaction as zope_transaction


class SiteBase(object):
    """A primitive site"""
    
    user_email_store_lower_case = True

    def __init__(self, *args, registry, transaction, db_session, redis, mailer, **kwargs):
        super().__init__(*args, **kwargs)
        self.registry = registry
        self.mailer = mailer
        self.transaction = transaction
        self.db_session = db_session
        self.redis = redis

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
                transaction_manager=tm, smtp_mailer=registry["sendgrid_mailer"]
            )

        return cls(**{
            "registry": registry,
            "transaction": tm,
            "db_session": db_session,
            "redis": registry["redis"],
            "mailer": mailer,
            **kwargs,
        })

    @classmethod
    def from_request(cls, request, **kwargs):
        """Create a site object from a request object"""
        kwargs = {
            'registry': request.registry,
            'db_session': request.db_session,
            'redis': request.redis,
            'mailer': request.mailer,
            'transaction': request.tm,
            **kwargs,
        }
        return cls(**kwargs)

    def identity_for_jwt_claims(self, claims):
        return None

    def principals_for_identity(self, identity):
        return []