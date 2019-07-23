from __future__ import print_function

# stdlib
import pdb
import unittest

# pypi
from webtest import TestApp

# local
from . import test_pyramid_app


# ==============================================================================


class _AppBackedTests(object):

    def setUp(self):
        app = test_pyramid_app.main({})
        self.testapp = TestApp(app)

    def _new_env(self):
        test_env = {
            'testapp': self.testapp,
            'extra_environ': {'wsgi.url_scheme': 'https',
                              'HTTP_HOST': 'app.example.com',
                              },
        }
        return test_env


class AppTests_Main(_AppBackedTests, unittest.TestCase):
    """
    this suite spins up an instance of the Pyramid test app (`test_pyramid_app`)
    """

    def test_splash(self):
        """
        the "splash" page does nothing. hitting means the app set up correctly.
        """
        test_env = self._new_env()
        res = self.testapp.get('/', extra_environ=test_env['extra_environ'])
        self.assertEqual(res.status_code, 200)

    def test_dbSession(self):
        test_env = self._new_env()
        res = self.testapp.get('/tests/dbSession', extra_environ=test_env['extra_environ'])
        self.assertEqual(res.status_code, 200)

    def test_dbSession_callbacks(self):
        test_env = self._new_env()
        res = self.testapp.get('/tests/dbSession/callbacks', extra_environ=test_env['extra_environ'])
        self.assertEqual(res.status_code, 200)


class AppTests_Reader(_AppBackedTests, unittest.TestCase):

    def test_core(self):
        test_env = self._new_env()
        res = self.testapp.get('/tests/dbSession_reader', extra_environ=test_env['extra_environ'])
        self.assertEqual(res.status_code, 200)

    def test_query(self):
        test_env = self._new_env()
        res = self.testapp.get('/tests/dbSession_reader/query', extra_environ=test_env['extra_environ'])
        self.assertEqual(res.status_code, 200)

    def test_query_status(self):
        test_env = self._new_env()
        res = self.testapp.get('/tests/dbSession_reader/query_status', extra_environ=test_env['extra_environ'])
        self.assertEqual(res.status_code, 200)


class AppTests_Writer(_AppBackedTests, unittest.TestCase):

    def test_core(self):
        test_env = self._new_env()
        res = self.testapp.get('/tests/dbSession_writer', extra_environ=test_env['extra_environ'])
        self.assertEqual(res.status_code, 200)

    def test_query(self):
        test_env = self._new_env()
        res = self.testapp.get('/tests/dbSession_writer/query', extra_environ=test_env['extra_environ'])
        self.assertEqual(res.status_code, 200)

    def test_query_status(self):
        test_env = self._new_env()
        res = self.testapp.get('/tests/dbSession_writer/query_status', extra_environ=test_env['extra_environ'])
        self.assertEqual(res.status_code, 200)


class AppTests_Mixed(_AppBackedTests, unittest.TestCase):

    def test_core(self):
        test_env = self._new_env()
        res = self.testapp.get('/tests/dbSession_mixed', extra_environ=test_env['extra_environ'])
        self.assertEqual(res.status_code, 200)

    def test_query(self):
        test_env = self._new_env()
        res = self.testapp.get('/tests/dbSession_mixed/query', extra_environ=test_env['extra_environ'])
        self.assertEqual(res.status_code, 200)

    def test_query_status(self):
        test_env = self._new_env()
        res = self.testapp.get('/tests/dbSession_mixed/query_status', extra_environ=test_env['extra_environ'])
        self.assertEqual(res.status_code, 200)
