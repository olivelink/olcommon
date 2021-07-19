from . import sendgrid_mailer
from .utils import yesish

import os
import sqlalchemy.orm
import sqlalchemy.pool
import redis


def configure_registry(registry: dict, settings: dict):
    """COnfigure a registry with a given set of settings
    """
    registry["settings"] = settings
    registry["is_debug"] = yesish(settings["is_debug"])

    assert registry["root_class"], "No root class defined in the registry"

    registry["null_pool_db_engine"] = sqlalchemy.create_engine(settings["postgresql_url"], poolclass=sqlalchemy.pool.NullPool)
    registry["null_pool_db_session_factory"] = sqlalchemy.orm.sessionmaker()
    registry["null_pool_db_session_factory"].configure(bind=registry["null_pool_db_engine"])
   
    registry["db_engine"] = sqlalchemy.create_engine(settings["postgresql_url"])
    registry["db_session_factory"] = sqlalchemy.orm.sessionmaker()
    registry["db_session_factory"].configure(bind=registry["db_engine"])

    registry["redis"] = redis.StrictRedis.from_url(
        settings["redis_url"], decode_responses=False
    )

    registry["site_email"] = settings["site_email"]
    registry["site_email_from_name"] = settings["site_email_from_name"]
    registry["site_noreply_email"] = settings["site_noreply_email"]
    registry["use_debug_mailer"] = yesish(os.environ.get("use_debug_mailer")) or registry["is_debug"]
    if registry["use_debug_mailer"] :
        registry["sendgrid_smtp_mailer"] = None
    else:
        registry["sendgrid_smtp_mailer"] = sendgrid_mailer.SendgridMailer(
            hostname=settings["mail.host"],
            port=settings["mail.port"],
            sendgrid_api_key=settings["sendgrid_api_key"],
            sendgrid_template_generic=settings["sendgrid_template_generic"],
        )