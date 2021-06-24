from .utils import yesish

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