# -*- coding:utf-8 -*-

import pyramid_session_redis

def includeme(config):
    registry = config.registry
    secret = registry["session_secret"][:32]
    session_factory = pyramid_session_redis.RedisSessionFactory(
        secret,
        timeout=registry['cookie_session_timeout'],
        cookie_name=f"{registry['cookie_prefix']}.s",        
        cookie_domain=registry["cookie_domain"],
        cookie_max_age=registry['cookie_session_timeout'],
        cookie_secure=registry["cookie_session_secure"],
        cookie_httponly=True,
        client_callable=lambda request, **kwargs: request.redis,
    )
    config.set_session_factory(session_factory)
