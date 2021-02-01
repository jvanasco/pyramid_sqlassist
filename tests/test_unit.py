from __future__ import print_function
from __future__ import unicode_literals

# stdlib
import pdb
import re
import unittest

# pyramid testing requirements
from pyramid import testing
from pyramid.interfaces import IRequestExtensions
from pyramid.response import Response
from pyramid.request import Request
from pyramid_tm.tests import DummyDataManager

# pypi
import sqlalchemy

# local
import pyramid_sqlassist
from .pyramid_testapp import model
from .pyramid_testapp.model import model_objects


# ==============================================================================


# used to ensure the toolbar link is injected into requests
re_toolbar_link = re.compile(r'(?:href="http://localhost)(/_debug_toolbar/[\d]+)"')


class _TestPyramidAppHarness(object):

    settings = {
        "mako.directories": ".",
        "sqlalchemy_reader.url": "sqlite://",
        "sqlalchemy_writer.url": "sqlite://",
        "sqlassist.use_zope": False,
        "sqlassist.is_scoped": False,
    }

    def setUp(self):
        self.config = testing.setUp()
        self.context = testing.DummyResource()
        self.request = testing.DummyRequest()

        engine_reader = sqlalchemy.engine_from_config(
            self.settings, prefix="sqlalchemy_reader."
        )
        pyramid_sqlassist.initialize_engine(
            "reader",
            engine_reader,
            is_default=False,
            model_package=model_objects,
            use_zope=self.settings.get("sqlassist.use_zope"),
            is_scoped=self.settings.get("sqlassist.is_scoped"),
        )

        engine_writer = sqlalchemy.engine_from_config(
            self.settings, prefix="sqlalchemy_writer."
        )
        pyramid_sqlassist.initialize_engine(
            "writer",
            engine_writer,
            is_default=False,
            model_package=model_objects,
            use_zope=self.settings.get("sqlassist.use_zope"),
            is_scoped=self.settings.get("sqlassist.is_scoped"),
        )
        pyramid_sqlassist.register_request_method(self.config, "dbSession")

        try:
            model_objects.DeclaredTable.metadata.create_all(engine_reader)
        except Exception as exc:
            print(exc)
        try:
            model_objects.DeclaredTable.metadata.create_all(engine_writer)
        except Exception as exc:
            print(exc)

    def tearDown(self):
        testing.tearDown()


class TestPyramidSetup(_TestPyramidAppHarness, unittest.TestCase):
    def test_pyramid_setup(self):
        """test configuring the request property worked"""
        exts = self.config.registry.getUtility(IRequestExtensions)
        self.assertTrue("dbSession" in exts.descriptors)


class TestPyramidRequest(_TestPyramidAppHarness, unittest.TestCase):
    def test_initial_state(self):
        """this must be manually copied over for testing"""
        self.assertNotIn("finished_callbacks", self.request.__dict__)
        self.request.dbSession = pyramid_sqlassist.DbSessionsContainer(self.request)
        self.assertIn("engines", self.request.dbSession._engine_status_tracker.__dict__)
        self.assertIn("reader", self.request.dbSession._engine_status_tracker.engines)
        self.assertIn("writer", self.request.dbSession._engine_status_tracker.engines)
        self.assertEqual(
            0, self.request.dbSession._engine_status_tracker.engines["reader"]
        )
        self.assertEqual(
            0, self.request.dbSession._engine_status_tracker.engines["writer"]
        )
        self.assertIn("finished_callbacks", self.request.__dict__)

    def test_query_reader(self):
        self.assertNotIn("finished_callbacks", self.request.__dict__)
        self.request.dbSession = pyramid_sqlassist.DbSessionsContainer(self.request)
        touched = self.request.dbSession.reader.query(
            model_objects.FooObject
        ).first()  # noqa
        self.assertEqual(
            1, self.request.dbSession._engine_status_tracker.engines["reader"]
        )
        self.assertEqual(
            0, self.request.dbSession._engine_status_tracker.engines["writer"]
        )
        self.assertIn("finished_callbacks", self.request.__dict__)

    def test_query_writer(self):
        self.assertNotIn("finished_callbacks", self.request.__dict__)
        self.request.dbSession = pyramid_sqlassist.DbSessionsContainer(self.request)
        touched = self.request.dbSession.writer.query(
            model_objects.FooObject
        ).first()  # noqa
        self.assertEqual(
            0, self.request.dbSession._engine_status_tracker.engines["reader"]
        )
        self.assertEqual(
            1, self.request.dbSession._engine_status_tracker.engines["writer"]
        )
        self.assertIn("finished_callbacks", self.request.__dict__)

    def test_query_mixed(self):
        self.assertNotIn("finished_callbacks", self.request.__dict__)
        self.request.dbSession = pyramid_sqlassist.DbSessionsContainer(self.request)
        touched = self.request.dbSession.reader.query(
            model_objects.FooObject
        ).first()  # noqa
        touched = self.request.dbSession.writer.query(
            model_objects.FooObject
        ).first()  # noqa
        self.assertEqual(
            1, self.request.dbSession._engine_status_tracker.engines["reader"]
        )
        self.assertEqual(
            1, self.request.dbSession._engine_status_tracker.engines["writer"]
        )
        self.assertIn("finished_callbacks", self.request.__dict__)


# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =


class _TestPyramidAppHarness_Transaction(_TestPyramidAppHarness):

    settings = {
        "mako.directories": ".",
        "sqlalchemy_reader.url": "sqlite://",
        "sqlalchemy_writer.url": "sqlite://",
        "sqlassist.use_zope": True,
        "sqlassist.is_scoped": True,
    }


class TestPyramidSetup_Transaction(
    _TestPyramidAppHarness_Transaction, TestPyramidSetup, unittest.TestCase
):
    pass


class TestPyramidRequest_Transaction(
    _TestPyramidAppHarness_Transaction, TestPyramidRequest, unittest.TestCase
):
    pass


# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =


class TestPyramidTm(unittest.TestCase):
    def setUp(self):
        self.config = (
            testing.setUp()
        )  # pyramid_tm.tests.TestIntegration.setUp : `testing.setUp(autocommit=False)``
        self.context = testing.DummyResource()
        self.request = testing.DummyRequest()

        settings = {
            "mako.directories": ".",
            "sqlalchemy_reader.url": "sqlite://",
            "sqlalchemy_writer.url": "sqlite://",
            "sqlassist.use_zope": True,
            "sqlassist.is_scoped": True,
        }

        engine_reader = sqlalchemy.engine_from_config(
            settings, prefix="sqlalchemy_reader."
        )
        pyramid_sqlassist.initialize_engine(
            "reader",
            engine_reader,
            is_default=False,
            model_package=model_objects,
            use_zope=settings.get("sqlassist.use_zope"),
            is_scoped=settings.get("sqlassist.is_scoped"),
        )
        engine_writer = sqlalchemy.engine_from_config(
            settings, prefix="sqlalchemy_writer."
        )
        pyramid_sqlassist.initialize_engine(
            "writer",
            engine_writer,
            is_default=False,
            model_package=model_objects,
            use_zope=settings.get("sqlassist.use_zope"),
            is_scoped=settings.get("sqlassist.is_scoped"),
        )
        pyramid_sqlassist.register_request_method(self.config, "dbSession")

        try:
            model_objects.DeclaredTable.metadata.create_all(engine_reader)
        except Exception as exc:
            print(exc)
        try:
            model_objects.DeclaredTable.metadata.create_all(engine_writer)
        except Exception as exc:
            print(exc)

    def tearDown(self):
        testing.tearDown()

    def test_tm__not_enabled(self):
        dm = DummyDataManager()

        # create a view
        def empty_view(request):
            with self.assertRaises(AttributeError) as cm:
                dm.bind(request.tm)
            self.assertEqual(
                cm.exception.args[0], "'Request' object has no attribute 'tm'"
            )
            return Response(
                "<html><head></head><body>OK</body></html>", content_type="text/html"
            )

        self.config.add_view(empty_view)

        # make the app
        app = self.config.make_wsgi_app()
        # make a request
        req1 = Request.blank("/")
        req1.remote_addr = "127.0.0.1"
        resp1 = req1.get_response(app)
        self.assertEqual(resp1.status_code, 200)
        self.assertEqual(dm.action, None)

    def test_tm__enabled_valid__commit(self):
        self.config.include("pyramid_tm")

        dm = DummyDataManager()

        # create a view
        def empty_view(request):
            dm.bind(request.tm)
            foo = request.dbSession.writer.query(
                model_objects.FooObject
            ).first()  # noqa
            return Response(
                "<html><head></head><body>OK</body></html>", content_type="text/html"
            )

        self.config.add_view(empty_view)

        # make the app
        app = self.config.make_wsgi_app()
        # make a request
        req1 = Request.blank("/")
        req1.remote_addr = "127.0.0.1"
        resp1 = req1.get_response(app)
        self.assertEqual(resp1.status_code, 200)
        self.assertEqual(dm.action, "commit")

    def test_tm__enabled_valid__abort(self):
        self.config.include("pyramid_tm")

        dm = DummyDataManager()

        # create a view
        def empty_view(request):
            dm.bind(request.tm)
            foo = request.dbSession.writer.query(
                model_objects.FooObject
            ).first()  # noqa
            raise ValueError

        self.config.add_view(empty_view)

        def exc_view(request):
            return "failure"

        self.config.add_view(exc_view, context=ValueError, renderer="string")

        # make the app
        app = self.config.make_wsgi_app()
        # make a request
        req1 = Request.blank("/")
        req1.remote_addr = "127.0.0.1"
        resp1 = req1.get_response(app)
        self.assertEqual(resp1.body, b"failure")
        self.assertEqual(dm.action, "abort")


# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =


class TestInitializeEngine(unittest.TestCase):
    def test_zope_requires_scope__fail(self):
        settings = {
            "sqlalchemy_reader.url": "sqlite://",
            "sqlassist.use_zope": True,
            "sqlassist.is_scoped": False,
        }
        engine_reader = sqlalchemy.engine_from_config(
            settings, prefix="sqlalchemy_reader."
        )
        with self.assertRaises(ValueError) as cm:
            pyramid_sqlassist.initialize_engine(
                "reader",
                engine_reader,
                is_default=False,
                model_package=model_objects,
                use_zope=settings.get("sqlassist.use_zope"),
                is_scoped=settings.get("sqlassist.is_scoped"),
            )
        self.assertEqual(
            cm.exception.args[0], "`zope.sqlalchemy` requires scoped sessions"
        )

    def test_zope_sessionmaker_params__pass(self):
        settings = {
            "sqlalchemy_reader.url": "sqlite://",
            "sqlassist.use_zope": True,
            "sqlassist.is_scoped": True,
        }
        engine_reader = sqlalchemy.engine_from_config(
            settings, prefix="sqlalchemy_reader."
        )
        pyramid_sqlassist.initialize_engine(
            "reader",
            engine_reader,
            is_default=False,
            model_package=model_objects,
            sa_sessionmaker_params={},
            use_zope=settings.get("sqlassist.use_zope"),
            is_scoped=settings.get("sqlassist.is_scoped"),
        )

    def test_zope_sessionmaker_params__fail(self):
        settings = {
            "sqlalchemy_reader.url": "sqlite://",
            "sqlassist.use_zope": True,
            "sqlassist.is_scoped": True,
        }
        engine_reader = sqlalchemy.engine_from_config(
            settings, prefix="sqlalchemy_reader."
        )
        with self.assertRaises(ValueError) as cm:
            pyramid_sqlassist.initialize_engine(
                "reader",
                engine_reader,
                is_default=False,
                model_package=model_objects,
                sa_sessionmaker_params={"extension": "foo"},
                use_zope=settings.get("sqlassist.use_zope"),
                is_scoped=settings.get("sqlassist.is_scoped"),
            )
        self.assertEqual(
            cm.exception.args[0],
            "`use_zope=True` is incompatible with `extension` in `sa_sessionmaker_params`",
        )

    def test_zope_requires_scope__pass(self):
        settings = {
            "sqlalchemy_reader.url": "sqlite://",
            "sqlassist.use_zope": True,
            "sqlassist.is_scoped": True,
        }
        engine_reader = sqlalchemy.engine_from_config(
            settings, prefix="sqlalchemy_reader."
        )
        pyramid_sqlassist.initialize_engine(
            "reader",
            engine_reader,
            is_default=False,
            model_package=model_objects,
            use_zope=settings.get("sqlassist.use_zope"),
            is_scoped=settings.get("sqlassist.is_scoped"),
        )

    def test_no_zope_is_scoped__pass(self):
        settings = {
            "sqlalchemy_reader.url": "sqlite://",
            "sqlassist.use_zope": False,
            "sqlassist.is_scoped": True,
        }
        engine_reader = sqlalchemy.engine_from_config(
            settings, prefix="sqlalchemy_reader."
        )
        pyramid_sqlassist.initialize_engine(
            "reader",
            engine_reader,
            is_default=False,
            model_package=model_objects,
            use_zope=settings.get("sqlassist.use_zope"),
            is_scoped=settings.get("sqlassist.is_scoped"),
        )

    def test_no_zope_not_scoped__pass(self):
        settings = {
            "sqlalchemy_reader.url": "sqlite://",
            "sqlassist.use_zope": False,
            "sqlassist.is_scoped": False,
        }
        engine_reader = sqlalchemy.engine_from_config(
            settings, prefix="sqlalchemy_reader."
        )
        pyramid_sqlassist.initialize_engine(
            "reader",
            engine_reader,
            is_default=False,
            model_package=model_objects,
            use_zope=settings.get("sqlassist.use_zope"),
            is_scoped=settings.get("sqlassist.is_scoped"),
        )


class TestModelObjectFunctions(_TestPyramidAppHarness, unittest.TestCase):
    def setUp(self):
        _TestPyramidAppHarness.setUp(self)
        self.request.dbSession = pyramid_sqlassist.DbSessionsContainer(self.request)
        model.insert_initial_records(self.request.dbSession.writer)

    def test__get__by__id(self):
        foo = model_objects.FooObject.get__by__id(self.request.dbSession.writer, 1)
        self.assertIsNotNone(foo)
        self.assertEqual(foo.id, 1)

        _query_ids = (1, 2, 3)
        foos = model_objects.FooObject.get__by__id(
            self.request.dbSession.writer, _query_ids
        )
        self.assertIsInstance(foos, list)
        self.assertEqual(len(foos), 3)
        self.assertSequenceEqual([i.id for i in foos], _query_ids)

        foo_alt = model_objects.FooObject.get__by__id(
            self.request.dbSession.writer, 11, id_column="id_alt"
        )
        self.assertIsNotNone(foo_alt)
        self.assertEqual(foo_alt.id, 1)
        self.assertEqual(foo_alt.id_alt, 11)

        _query_ids_alt = (11, 12, 13)
        foos_alt = model_objects.FooObject.get__by__id(
            self.request.dbSession.writer, _query_ids_alt, id_column="id_alt"
        )
        self.assertIsInstance(foos_alt, list)
        self.assertEqual(len(foos_alt), 3)
        self.assertSequenceEqual([i.id_alt for i in foos], _query_ids_alt)

    def test__get__by__column__lower(self):
        self.assertRaises(
            ValueError,
            model_objects.FooObject.get__by__column__lower,
            self.request.dbSession.writer,
            "status",
            "AAAAA",
        )
        foos = model_objects.FooObject.get__by__column__lower(
            self.request.dbSession.writer, "status", "AAAAA", allow_many=True
        )
        self.assertIsInstance(foos, list)
        self.assertEqual(len(foos), 2)
        self.assertSequenceEqual([i.id for i in foos], (1, 2))

        foo_alt = model_objects.FooObject.get__by__column__lower(
            self.request.dbSession.writer, "status", "BBBBB"
        )
        self.assertIsNotNone(foo_alt)
        self.assertEqual(foo_alt.id, 3)

        foo_alt2 = model_objects.FooObject.get__by__column__lower(
            self.request.dbSession.writer, "status", "CCCCC"
        )
        self.assertIsNotNone(foo_alt2)
        self.assertEqual(foo_alt2.id, 4)

    def test__get__by__column__similar(self):
        foos = model_objects.FooObject.get__by__column__similar(
            self.request.dbSession.writer, "status", "A", prefix_only=True
        )
        self.assertIsInstance(foos, list)
        self.assertEqual(len(foos), 2)
        self.assertSequenceEqual([i.id for i in foos], (1, 2))

        foos2 = model_objects.FooObject.get__by__column__similar(
            self.request.dbSession.writer, "status_alt", "D", prefix_only=True
        )
        self.assertIsInstance(foos2, list)
        self.assertEqual(len(foos2), 1)
        self.assertEqual(foos2[0].id, 3)

        foos3 = model_objects.FooObject.get__by__column__similar(
            self.request.dbSession.writer, "status_alt", "D", prefix_only=False
        )
        self.assertIsInstance(foos3, list)
        self.assertEqual(len(foos3), 2)
        self.assertSequenceEqual([i.id for i in foos3], (3, 4))

    def test__get__by__column__exact_then_ilike(self):
        foo1 = model_objects.FooObject.get__by__column__exact_then_ilike(
            self.request.dbSession.writer, "status", "AAAAA"
        )
        self.assertIsNotNone(foo1)
        self.assertEqual(foo1.id, 1)

        foo2 = model_objects.FooObject.get__by__column__exact_then_ilike(
            self.request.dbSession.writer, "status", "aaaaa"
        )
        self.assertIsNotNone(foo2)
        self.assertEqual(foo2.id, 2)

        foo3 = model_objects.FooObject.get__by__column__exact_then_ilike(
            self.request.dbSession.writer, "status", "BBBBB"
        )
        self.assertIsNotNone(foo3)
        self.assertEqual(foo3.id, 3)

        foo3b = model_objects.FooObject.get__by__column__exact_then_ilike(
            self.request.dbSession.writer, "status", "bbbbb"
        )
        self.assertIsNotNone(foo3b)
        self.assertEqual(foo3b.id, 3)

    def test__get__range(self):
        # get them all
        foos = model_objects.FooObject.get__range(self.request.dbSession.writer)
        self.assertIsInstance(foos, list)
        self.assertEqual(len(foos), 4)

        foos = model_objects.FooObject.get__range(
            self.request.dbSession.writer, limit=2
        )
        self.assertIsInstance(foos, list)
        self.assertEqual(len(foos), 2)
        self.assertSequenceEqual([i.id for i in foos], (1, 2))

        foos = model_objects.FooObject.get__range(
            self.request.dbSession.writer, limit=2, sort_direction="desc"
        )
        self.assertIsInstance(foos, list)
        self.assertEqual(len(foos), 2)
        self.assertSequenceEqual([i.id for i in foos], (4, 3))

        foos = model_objects.FooObject.get__range(
            self.request.dbSession.writer, offset=1, limit=2
        )
        self.assertIsInstance(foos, list)
        self.assertEqual(len(foos), 2)
        self.assertSequenceEqual([i.id for i in foos], (2, 3))

        foos = model_objects.FooObject.get__range(
            self.request.dbSession.writer, offset=1, limit=2, sort_direction="desc"
        )
        self.assertIsInstance(foos, list)
        self.assertEqual(len(foos), 2)
        self.assertSequenceEqual([i.id for i in foos], (3, 2))

        foos = model_objects.FooObject.get__range(
            self.request.dbSession.writer, limit=2, order_col="status"
        )
        self.assertIsInstance(foos, list)
        self.assertEqual(len(foos), 2)
        self.assertSequenceEqual([i.id for i in foos], (1, 3))

        foos = model_objects.FooObject.get__range(
            self.request.dbSession.writer,
            limit=2,
            order_col="status",
            order_case_sensitive=False,
        )
        self.assertIsInstance(foos, list)
        self.assertEqual(len(foos), 2)
        self.assertSequenceEqual([i.id for i in foos], (1, 2))

    def test__loaded_columns_as_dict(self):
        # test all columns
        foo1 = (
            self.request.dbSession.writer.query(model_objects.FooObject)
            .filter(model_objects.FooObject.id == 1)
            .first()
        )
        self.assertIsNotNone(foo1)
        self.assertEqual(foo1.id, 1)
        as_dict = foo1.loaded_columns_as_dict()
        self.assertIsInstance(as_dict, dict)
        _all_column_names = [i.name for i in model_objects.FooObject.__table__.c]
        self.assertSequenceEqual(sorted(as_dict.keys()), sorted(_all_column_names))

        # test loadonly
        foo2 = (
            self.request.dbSession.writer.query(model_objects.FooObject)
            .filter(model_objects.FooObject.id == 2)
            .options(sqlalchemy.orm.load_only("status"))
            .first()
        )
        self.assertIsNotNone(foo2)
        self.assertEqual(foo2.id, 2)
        as_dict = foo2.loaded_columns_as_dict()
        self.assertIsInstance(as_dict, dict)
        _expected_column_names = [
            "id",
            "status",
        ]  #  sqlalchemy upgrades the query to use the fkey "id"
        self.assertSequenceEqual(sorted(as_dict.keys()), sorted(_expected_column_names))

    def test__loaded_columns_as_list(self):
        # first, names only...

        # test all columns
        foo1 = (
            self.request.dbSession.writer.query(model_objects.FooObject)
            .filter(model_objects.FooObject.id == 1)
            .first()
        )
        self.assertIsNotNone(foo1)
        self.assertEqual(foo1.id, 1)
        as_list = foo1.loaded_columns_as_list()
        self.assertIsInstance(as_list, list)
        _all_column_names = [i.name for i in model_objects.FooObject.__table__.c]
        self.assertSequenceEqual(sorted(as_list), sorted(_all_column_names))

        # test loadonly
        foo2 = (
            self.request.dbSession.writer.query(model_objects.FooObject)
            .filter(model_objects.FooObject.id == 2)
            .options(sqlalchemy.orm.load_only("status"))
            .first()
        )
        self.assertIsNotNone(foo2)
        self.assertEqual(foo2.id, 2)
        as_list = foo2.loaded_columns_as_list()
        self.assertIsInstance(as_list, list)
        _expected_column_names = [
            "id",
            "status",
        ]  # sqlalchemy upgrades the query to use the fkey "id"
        self.assertSequenceEqual(sorted(as_list), sorted(_expected_column_names))

        # then, with values...
        as_list2 = foo1.loaded_columns_as_list(with_values=True)
        self.assertIsInstance(as_list2, list)
        self.assertSequenceEqual(
            sorted([i[0] for i in as_list2]), sorted(_all_column_names)
        )

        as_list2 = foo2.loaded_columns_as_list(with_values=True)
        self.assertIsInstance(as_list2, list)
        self.assertSequenceEqual(
            sorted([i[0] for i in as_list2]), sorted(_expected_column_names)
        )

    def test__pyramid_request(self):
        foo = model_objects.FooObject.get__by__id(self.request.dbSession.writer, 1)
        self.assertIsNotNone(foo)
        self.assertEqual(foo.id, 1)
        self.assertEqual(foo._pyramid_request, self.request)


class TestDebugtoolbarPanel(_TestPyramidAppHarness, unittest.TestCase):
    def setUp(self):
        _TestPyramidAppHarness.setUp(self)
        self.config.add_settings(
            {"debugtoolbar.includes": "pyramid_sqlassist.debugtoolbar"}
        )
        self.config.include("pyramid_mako")
        self.config.include("pyramid_debugtoolbar")

    def test_panel_injected(self):

        # create a view
        def empty_view(request):
            return Response(
                "<html><head></head><body>OK</body></html>", content_type="text/html"
            )

        self.config.add_view(empty_view)

        # make the app
        app = self.config.make_wsgi_app()
        # make a request
        req1 = Request.blank("/")
        req1.remote_addr = "127.0.0.1"
        resp1 = req1.get_response(app)
        self.assertEqual(resp1.status_code, 200)
        self.assertIn("http://localhost/_debug_toolbar/", resp1.text)

        # check the toolbar
        links = re_toolbar_link.findall(resp1.text)
        self.assertIsNotNone(links)
        self.assertIsInstance(links, list)
        self.assertEqual(len(links), 1)
        toolbar_link = links[0]

        req2 = Request.blank(toolbar_link)
        req2.remote_addr = "127.0.0.1"
        resp2 = req2.get_response(app)
        self.assertEqual(resp2.status_code, 200)

        self.assertIn("<h3>SQLAssist</h3>", resp2.text)
        self.assertIn(
            "The SQLAssist <code>`DbSessionsContainer`</code> is registered onto the Pyramid `Request` object as <code>request.dbSession</code>.",
            resp2.text,
        )
        self.assertIn("No connections were active on this `request`.", resp2.text)

    def test_panel_tracks(self):

        # create a view
        def empty_view(request):
            foo = request.dbSession.writer.query(
                model_objects.FooObject
            ).first()  # noqa
            return Response(
                "<html><head></head><body>OK</body></html>", content_type="text/html"
            )

        self.config.add_view(empty_view)

        # make the app
        app = self.config.make_wsgi_app()
        # make a request
        req1 = Request.blank("/")
        req1.remote_addr = "127.0.0.1"
        resp1 = req1.get_response(app)
        self.assertEqual(resp1.status_code, 200)
        self.assertIn("http://localhost/_debug_toolbar/", resp1.text)

        # check the toolbar
        links = re_toolbar_link.findall(resp1.text)
        self.assertIsNotNone(links)
        self.assertIsInstance(links, list)
        self.assertEqual(len(links), 1)
        toolbar_link = links[0]

        req2 = Request.blank(toolbar_link)
        req2.remote_addr = "127.0.0.1"
        resp2 = req2.get_response(app)
        self.assertEqual(resp2.status_code, 200)

        self.assertIn("<h3>SQLAssist</h3>", resp2.text)
        self.assertIn(
            "The SQLAssist <code>`DbSessionsContainer`</code> is registered onto the Pyramid `Request` object as <code>request.dbSession</code>.",
            resp2.text,
        )
        self.assertNotIn("No connections were active on this `request`.", resp2.text)
        self.assertIn("<h3>Active on this Request</h3>", resp2.text)
        # the object type could be `sqlalchemy.orm.scroping.scoped_session` or `sqlalchemy.orm.session.Session`
        self.assertIn(
            """<p>\n\t\tThe SQLAssist <code>`DbSessionsContainer`</code> is registered onto the Pyramid `Request` object as <code>request.dbSession</code>.\n\t</p>\n\t\n\t\n\t<h3>Active on this Request</h3>\n\t\n\t\t<table class="table table-striped table-condensed">\n\t\t\t<thead>\n\t\t\t\t<tr>\n\t\t\t\t\t<th>connection</th>\n\t\t\t\t\t<th>connection object</th>\n\t\t\t\t</tr>\n\t\t\t</thead>\n\t\t\t<tbody>\n\t\t\t\t\t<tr>\n\t\t\t\t\t\t<th>writer</th>\n\t\t\t\t\t\t<td>&lt;sqlalchemy.orm.""",
            resp2.text,
        )


# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
