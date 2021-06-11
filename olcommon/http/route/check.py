# -*- coding: utf-8 -*-

from pyramid.response import Response
from pyramid.view import view_config
from pyramid.view import view_defaults


@view_defaults(route_name="check", physical_path=("",))
class CheckView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

    @view_config(name="app")
    def app(self):
        """An always successful view"""
        return Response(body="200 ok app", content_type="text/plain")

    @view_config(name="db")
    def db(self):
        """A view which checks database connectivity"""
        try:
            result = self.request.db_session.execute("select 1;")
            assert result.first() == (1,)
        except Exception:
            return Response(
                status_code=500,
                body="500 error connecting to db",
                content_type="text/plain",
            )
        return Response(body="200 ok db", content_type="text/plain")

    @view_config(name="redis")
    def redis(self):
        """A view which checks database connectivity"""
        try:
            result = self.request.redis.info()
            assert result["redis_version"]
        except Exception:
            return Response(
                status_code=500,
                body="500 error connecting to redis",
                content_type="text/plain",
            )
        return Response(body="200 ok redis", content_type="text/plain")
