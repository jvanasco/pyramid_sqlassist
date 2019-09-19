from __future__ import print_function


import logging

log = logging.getLogger(__name__)

"""
fake app for tests
"""
# stdlib
import pdb

# pyramid
from pyramid.view import view_config

# pypi
from pyramid_sqlassist import DbSessionsContainer
from sqlalchemy.orm.session import Session as SqlalchemySession
from sqlalchemy.orm.scoping import scoped_session as scoped_session

# local
from .model.model_objects import FooObject

# ==============================================================================


class Handler(object):
    def __init__(self, request):
        self.request = request


class Splash(Handler):
    @view_config(route_name="splash", renderer="templates/splash.mako")
    def splash(self):
        return {}


class TestsDbsession(Handler):
    @view_config(route_name="test:dbSession", renderer="templates/test_results.mako")
    def test_core(self):
        if not isinstance(self.request.dbSession, DbSessionsContainer):
            raise ValueError("`self.request.dbSession` is not a `DbSessionsContainer`")
        return {}

    @view_config(
        route_name="test:dbSession:callbacks", renderer="templates/test_results.mako"
    )
    def test_callbacks(self):
        if "finished_callbacks" in self.request.__dict__:
            raise ValueError(
                "`request` has 'finished_callbacks' before one has been registered."
            )
        touched = self.request.dbSession  # noqa
        if "finished_callbacks" not in self.request.__dict__:
            raise ValueError("`request` does not have 'finished_callbacks', it should")
        return {}


class TestsDbsessionReader(Handler):
    @view_config(
        route_name="test:dbSession_reader", renderer="templates/test_results.mako"
    )
    def test_core(self):
        if self.request.registry.settings.get("sqlassist.is_scoped"):
            if not isinstance(self.request.dbSession.reader, scoped_session):
                raise ValueError(
                    "`self.request.dbSession.reader` is not a `scoped_session`"
                )
        else:
            if not isinstance(self.request.dbSession.reader, SqlalchemySession):
                raise ValueError(
                    "`self.request.dbSession.reader` is not a `SqlalchemySession`"
                )
        return {}

    @view_config(
        route_name="test:dbSession_reader:query", renderer="templates/test_results.mako"
    )
    def test_query(self):
        foo = self.request.dbSession.reader.query(FooObject).first()  # noqa
        return {}

    @view_config(
        route_name="test:dbSession_reader:query_status",
        renderer="templates/test_results.mako",
    )
    def test_query_status(self):
        foo = self.request.dbSession.reader.query(FooObject).first()  # noqa
        if "reader" not in self.request.dbSession.__dict__:
            raise ValueError("`reader` did not memoize into `self.request.dbSession`")
        if "writer" in self.request.dbSession.__dict__:
            raise ValueError(
                "`writer` should not memoize into `self.request.dbSession`"
            )
        return {}


class TestsDbsessionWriter(Handler):
    @view_config(
        route_name="test:dbSession_writer", renderer="templates/test_results.mako"
    )
    def test_core(self):
        if self.request.registry.settings.get("sqlassist.is_scoped"):
            if not isinstance(self.request.dbSession.writer, scoped_session):
                raise ValueError(
                    "`self.request.dbSession.writer` is not a `scoped_session`"
                )
        else:
            if not isinstance(self.request.dbSession.writer, SqlalchemySession):
                raise ValueError(
                    "`self.request.dbSession.writer` is not a `SqlalchemySession`"
                )
        return {}

    @view_config(
        route_name="test:dbSession_writer:query", renderer="templates/test_results.mako"
    )
    def test_query(self):
        foo = self.request.dbSession.writer.query(FooObject).first()  # noqa
        return {}

    @view_config(
        route_name="test:dbSession_writer:query_status",
        renderer="templates/test_results.mako",
    )
    def test_query_status(self):
        foo = self.request.dbSession.writer.query(FooObject).first()  # noqa
        if "reader" in self.request.dbSession.__dict__:
            raise ValueError(
                "`reader` should not memoize into `self.request.dbSession`"
            )
        if "writer" not in self.request.dbSession.__dict__:
            raise ValueError("`writer` did not memoize into `self.request.dbSession`")
        return {}


class TestsDbsessionMixed(Handler):
    @view_config(
        route_name="test:dbSession_mixed", renderer="templates/test_results.mako"
    )
    def test_core(self):
        if self.request.registry.settings.get("sqlassist.is_scoped"):
            if not isinstance(self.request.dbSession.reader, scoped_session):
                raise ValueError(
                    "`self.request.dbSession.reader` is not a `scoped_session`"
                )
            if not isinstance(self.request.dbSession.writer, scoped_session):
                raise ValueError(
                    "`self.request.dbSession.writer` is not a `scoped_session`"
                )
        else:
            if not isinstance(self.request.dbSession.reader, SqlalchemySession):
                raise ValueError(
                    "`self.request.dbSession.reader` is not a `SqlalchemySession`"
                )
            if not isinstance(self.request.dbSession.writer, SqlalchemySession):
                raise ValueError(
                    "`self.request.dbSession.writer` is not a `SqlalchemySession`"
                )
        return {}

    @view_config(
        route_name="test:dbSession_mixed:query", renderer="templates/test_results.mako"
    )
    def test_query(self):
        foo1 = self.request.dbSession.reader.query(FooObject).first()  # noqa
        foo2 = self.request.dbSession.writer.query(FooObject).first()  # noqa
        return {}

    @view_config(
        route_name="test:dbSession_mixed:query_status",
        renderer="templates/test_results.mako",
    )
    def test_query_status(self):
        foo1 = self.request.dbSession.reader.query(FooObject).first()  # noqa
        foo2 = self.request.dbSession.writer.query(FooObject).first()  # noqa
        if "reader" not in self.request.dbSession.__dict__:
            raise ValueError("`reader` did not memoize into `self.request.dbSession`")
        if "writer" not in self.request.dbSession.__dict__:
            raise ValueError("`writer` did not memoize into `self.request.dbSession`")
        return {}
