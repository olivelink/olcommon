from .utils import yesish
from . import database
from pyramid.path import DottedNameResolver

import sqlalchemy.orm
import redis


def configure_registry(registry: dict, settings: dict):
    """COnfigure a registry with a given set of settings
    """
    registry["is_debug"] = yesish(settings["is_debug"])
    
    registry["root_class"] = DottedNameResolver().resolve(settings["root_class"])
    database.configure_registry(registry, settings)

    registry["db_engine"] = sqlalchemy.engine_from_config(settings, "sqlalchemy.")
    registry["db_session_factory"] = sqlalchemy.orm.sessionmaker()
    registry["db_session_factory"].configure(bind=registry["db_engine"])

    registry["redis"] = redis.StrictRedis.from_url(
        settings["redis_url"], decode_responses=False
    )