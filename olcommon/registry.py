from .utils import yesish

import sqlalchemy.orm
import redis


def configure_registry(registry: dict, settings: dict):
    """COnfigure a registry with a given set of settings
    """
    registry["is_debug"] = yesish(settings["is_debug"])

    assert registry["root_class"], "No root class defined in the registry"
    
    registry["db_engine"] = sqlalchemy.engine_from_config(settings, "sqlalchemy.")
    registry["db_session_factory"] = sqlalchemy.orm.sessionmaker()
    registry["db_session_factory"].configure(bind=registry["db_engine"])

    registry["redis"] = redis.StrictRedis.from_url(
        settings["redis_url"], decode_responses=False
    )