from __future__ import print_function

# stdlib
import unittest
import pdb


# pyramid testing requirements
from pyramid import testing
from pyramid.interfaces import IRequestExtensions

# pypi
import sqlalchemy

# local
import pyramid_sqlassist
from .test_pyramid_app import model
from .test_pyramid_app.model import model_objects


# ==============================================================================



class TestPyramidAppHarness(object):

    def setUp(self):
        self.config = testing.setUp()
        self.settings = {'mako.directories': '.',
                         'sqlalchemy_reader.url': 'sqlite://',
                         'sqlalchemy_writer.url': 'sqlite://',
                         }
        self.context = testing.DummyResource()
        self.request = testing.DummyRequest()

        engine_reader = sqlalchemy.engine_from_config(self.settings,
                                                      prefix="sqlalchemy_reader.",
                                                      )
        pyramid_sqlassist.initialize_engine('reader',
                                            engine_reader,
                                            is_default=False,
                                            model_package=model_objects,
                                            use_zope=False,
                                            )

        engine_writer = sqlalchemy.engine_from_config(self.settings,
                                                      prefix="sqlalchemy_writer.",
                                                      )
        pyramid_sqlassist.initialize_engine('writer',
                                            engine_writer,
                                            is_default=False,
                                            model_package=model_objects,
                                            use_zope=False,
                                            )
        pyramid_sqlassist.register_request_method(self.config, 'dbSession')
    
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


class TestPyramidSetup(TestPyramidAppHarness, unittest.TestCase):

    def test_pyramid_setup(self):
        """test configuring the request property worked"""
        exts = self.config.registry.getUtility(IRequestExtensions)
        self.assertTrue('dbSession' in exts.descriptors)


class TestPyramidRequest(TestPyramidAppHarness, unittest.TestCase):

    def test_initial_state(self):
        """this must be manually copied over for testing"""
        self.assertNotIn('finished_callbacks', self.request.__dict__)
        self.request.dbSession = pyramid_sqlassist.DbSessionsContainer(self.request)
        self.assertIn('engines', self.request.dbSession._engine_status_tracker.__dict__)
        self.assertIn('reader', self.request.dbSession._engine_status_tracker.engines)
        self.assertIn('writer', self.request.dbSession._engine_status_tracker.engines)
        self.assertEqual(0, self.request.dbSession._engine_status_tracker.engines['reader'])
        self.assertEqual(0, self.request.dbSession._engine_status_tracker.engines['writer'])
        self.assertIn('finished_callbacks', self.request.__dict__)

    def test_query_reader(self):
        self.assertNotIn('finished_callbacks', self.request.__dict__)
        self.request.dbSession = pyramid_sqlassist.DbSessionsContainer(self.request)
        touched = self.request.dbSession.reader.query(model_objects.FooObject).first()
        self.assertEqual(1, self.request.dbSession._engine_status_tracker.engines['reader'])
        self.assertEqual(0, self.request.dbSession._engine_status_tracker.engines['writer'])
        self.assertIn('finished_callbacks', self.request.__dict__)

    def test_query_writer(self):
        self.assertNotIn('finished_callbacks', self.request.__dict__)
        self.request.dbSession = pyramid_sqlassist.DbSessionsContainer(self.request)
        touched = self.request.dbSession.writer.query(model_objects.FooObject).first()
        self.assertEqual(0, self.request.dbSession._engine_status_tracker.engines['reader'])
        self.assertEqual(1, self.request.dbSession._engine_status_tracker.engines['writer'])
        self.assertIn('finished_callbacks', self.request.__dict__)

    def test_query_mixed(self):
        self.assertNotIn('finished_callbacks', self.request.__dict__)
        self.request.dbSession = pyramid_sqlassist.DbSessionsContainer(self.request)
        touched = self.request.dbSession.reader.query(model_objects.FooObject).first()
        touched = self.request.dbSession.writer.query(model_objects.FooObject).first()
        self.assertEqual(1, self.request.dbSession._engine_status_tracker.engines['reader'])
        self.assertEqual(1, self.request.dbSession._engine_status_tracker.engines['writer'])
        self.assertIn('finished_callbacks', self.request.__dict__)


class TestModelObjectFunctions(TestPyramidAppHarness, unittest.TestCase):

    def setUp(self):
        TestPyramidAppHarness.setUp(self)
        self.request.dbSession = pyramid_sqlassist.DbSessionsContainer(self.request)
        model.insert_initial_records(self.request.dbSession.writer)

    def test__get__by__id(self):
        foo = model_objects.FooObject.get__by__id(self.request.dbSession.writer, 1)
        self.assertIsNotNone(foo)
        self.assertEqual(foo.id, 1)

        _query_ids = (1, 2, 3)
        foos = model_objects.FooObject.get__by__id(self.request.dbSession.writer, _query_ids)
        self.assertIsInstance(foos, list)
        self.assertEqual(len(foos), 3)
        self.assertSequenceEqual([i.id for i in foos], _query_ids)

        foo_alt = model_objects.FooObject.get__by__id(self.request.dbSession.writer, 11, id_column='id_alt')
        self.assertIsNotNone(foo_alt)
        self.assertEqual(foo_alt.id, 1)
        self.assertEqual(foo_alt.id_alt, 11)

        _query_ids_alt = (11, 12, 13)
        foos_alt = model_objects.FooObject.get__by__id(self.request.dbSession.writer, _query_ids_alt, id_column='id_alt')
        self.assertIsInstance(foos_alt, list)
        self.assertEqual(len(foos_alt), 3)
        self.assertSequenceEqual([i.id_alt for i in foos], _query_ids_alt)
        

    def test__get__by__column__lower(self):
        self.assertRaises(ValueError,
                          model_objects.FooObject.get__by__column__lower,
                          self.request.dbSession.writer,
                          'status',
                          'AAAAA'
                          )
        foos = model_objects.FooObject.get__by__column__lower(self.request.dbSession.writer, 'status', 'AAAAA', allow_many=True)
        self.assertIsInstance(foos, list)
        self.assertEqual(len(foos), 2)
        self.assertSequenceEqual([i.id for i in foos], (1, 2))

        foo_alt = model_objects.FooObject.get__by__column__lower(self.request.dbSession.writer, 'status', 'BBBBB')
        self.assertIsNotNone(foo_alt)
        self.assertEqual(foo_alt.id, 3)

        foo_alt2 = model_objects.FooObject.get__by__column__lower(self.request.dbSession.writer, 'status', 'CCCCC')
        self.assertIsNotNone(foo_alt2)
        self.assertEqual(foo_alt2.id, 4)

    def test__get__by__column__similar(self):
        foos = model_objects.FooObject.get__by__column__similar(self.request.dbSession.writer, 'status', 'A', prefix_only=True)
        self.assertIsInstance(foos, list)
        self.assertEqual(len(foos), 2)
        self.assertSequenceEqual([i.id for i in foos], (1, 2))

        foos2 = model_objects.FooObject.get__by__column__similar(self.request.dbSession.writer, 'status_alt', 'D', prefix_only=True)
        self.assertIsInstance(foos2, list)
        self.assertEqual(len(foos2), 1)
        self.assertEqual(foos2[0].id, 3)

        foos3 = model_objects.FooObject.get__by__column__similar(self.request.dbSession.writer, 'status_alt', 'D', prefix_only=False)
        self.assertIsInstance(foos3, list)
        self.assertEqual(len(foos3), 2)
        self.assertSequenceEqual([i.id for i in foos3], (3, 4))

    def test__get__by__column__exact_then_ilike(self):
        foo1 = model_objects.FooObject.get__by__column__exact_then_ilike(self.request.dbSession.writer, 'status', 'AAAAA')
        self.assertIsNotNone(foo1)
        self.assertEqual(foo1.id, 1)

        foo2 = model_objects.FooObject.get__by__column__exact_then_ilike(self.request.dbSession.writer, 'status', 'aaaaa')
        self.assertIsNotNone(foo2)
        self.assertEqual(foo2.id, 2)

        foo3 = model_objects.FooObject.get__by__column__exact_then_ilike(self.request.dbSession.writer, 'status', 'BBBBB')
        self.assertIsNotNone(foo3)
        self.assertEqual(foo3.id, 3)

        foo3b = model_objects.FooObject.get__by__column__exact_then_ilike(self.request.dbSession.writer, 'status', 'bbbbb')
        self.assertIsNotNone(foo3b)
        self.assertEqual(foo3b.id, 3)

    def test__get__range(self):
        # get them all
        foos = model_objects.FooObject.get__range(self.request.dbSession.writer)
        self.assertIsInstance(foos, list)
        self.assertEqual(len(foos), 4)

        foos = model_objects.FooObject.get__range(self.request.dbSession.writer, limit=2)
        self.assertIsInstance(foos, list)
        self.assertEqual(len(foos), 2)
        self.assertSequenceEqual([i.id for i in foos], (1, 2))

        foos = model_objects.FooObject.get__range(self.request.dbSession.writer, limit=2, sort_direction='desc')
        self.assertIsInstance(foos, list)
        self.assertEqual(len(foos), 2)
        self.assertSequenceEqual([i.id for i in foos], (4, 3))

        foos = model_objects.FooObject.get__range(self.request.dbSession.writer, offset=1, limit=2)
        self.assertIsInstance(foos, list)
        self.assertEqual(len(foos), 2)
        self.assertSequenceEqual([i.id for i in foos], (2, 3))

        foos = model_objects.FooObject.get__range(self.request.dbSession.writer, offset=1, limit=2, sort_direction='desc')
        self.assertIsInstance(foos, list)
        self.assertEqual(len(foos), 2)
        self.assertSequenceEqual([i.id for i in foos], (3, 2))

        foos = model_objects.FooObject.get__range(self.request.dbSession.writer, limit=2, order_col='status')
        self.assertIsInstance(foos, list)
        self.assertEqual(len(foos), 2)
        self.assertSequenceEqual([i.id for i in foos], (1, 3))

        foos = model_objects.FooObject.get__range(self.request.dbSession.writer, limit=2, order_col='status', order_case_sensitive=False)
        self.assertIsInstance(foos, list)
        self.assertEqual(len(foos), 2)
        self.assertSequenceEqual([i.id for i in foos], (1, 2))

    def test__loaded_columns_as_dict(self):
        # test all columns
        foo1 = self.request.dbSession.writer.query(model_objects.FooObject)\
            .filter(model_objects.FooObject.id==1)\
            .first()
        self.assertIsNotNone(foo1)
        self.assertEqual(foo1.id, 1)
        as_dict = foo1.loaded_columns_as_dict()
        self.assertIsInstance(as_dict, dict)
        _all_column_names = [i.name for i in model_objects.FooObject.__table__.c]
        self.assertSequenceEqual(sorted(as_dict.keys()), sorted(_all_column_names))

        # test loadonly
        foo2 = self.request.dbSession.writer.query(model_objects.FooObject)\
            .filter(model_objects.FooObject.id==2)\
            .options(sqlalchemy.orm.load_only('status'))\
            .first()
        self.assertIsNotNone(foo2)
        self.assertEqual(foo2.id, 2)
        as_dict = foo2.loaded_columns_as_dict()
        self.assertIsInstance(as_dict, dict)
        _expected_column_names = ['id', 'status', ]  #  sqlalchemy upgrades the query to use the fkey "id"
        self.assertSequenceEqual(sorted(as_dict.keys()), sorted(_expected_column_names))

    def test__loaded_columns_as_list(self):
        # first, names only...
    
        # test all columns
        foo1 = self.request.dbSession.writer.query(model_objects.FooObject)\
            .filter(model_objects.FooObject.id==1)\
            .first()
        self.assertIsNotNone(foo1)
        self.assertEqual(foo1.id, 1)
        as_list = foo1.loaded_columns_as_list()
        self.assertIsInstance(as_list, list)
        _all_column_names = [i.name for i in model_objects.FooObject.__table__.c]
        self.assertSequenceEqual(sorted(as_list), sorted(_all_column_names))

        # test loadonly
        foo2 = self.request.dbSession.writer.query(model_objects.FooObject)\
            .filter(model_objects.FooObject.id==2)\
            .options(sqlalchemy.orm.load_only('status'))\
            .first()
        self.assertIsNotNone(foo2)
        self.assertEqual(foo2.id, 2)
        as_list = foo2.loaded_columns_as_list()
        self.assertIsInstance(as_list, list)
        _expected_column_names = ['id', 'status', ]  #  sqlalchemy upgrades the query to use the fkey "id"
        self.assertSequenceEqual(sorted(as_list), sorted(_expected_column_names))

        # then, with values...
        as_list2 = foo1.loaded_columns_as_list(with_values=True)
        self.assertIsInstance(as_list2, list)
        self.assertSequenceEqual(sorted([i[0] for i in as_list2]), sorted(_all_column_names))

        as_list2 = foo2.loaded_columns_as_list(with_values=True)
        self.assertIsInstance(as_list2, list)
        self.assertSequenceEqual(sorted([i[0] for i in as_list2]), sorted(_expected_column_names))

    def test__pyramid_request(self):
        foo = model_objects.FooObject.get__by__id(self.request.dbSession.writer, 1)
        self.assertIsNotNone(foo)
        self.assertEqual(foo.id, 1)
        self.assertEqual(foo._pyramid_request, self.request)
