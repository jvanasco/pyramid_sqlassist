from __future__ import print_function

# stdlib
import pdb
import unittest

# pypi
from webtest import TestApp

# local
from . import pyramid_testapp


# ==============================================================================


class _AppBackedTests(object):
    def setUp(self):
        app_test_settings = {"sqlassist.use_zope": False, "sqlassist.is_scoped": False}
        app = pyramid_testapp.main({}, **app_test_settings)
        self.testapp = TestApp(app)

    def _new_env(self):
        test_env = {
            "testapp": self.testapp,
            "extra_environ": {
                "wsgi.url_scheme": "https",
                "HTTP_HOST": "app.example.com",
            },
        }
        return test_env


class AppTests_Main(_AppBackedTests, unittest.TestCase):
    """
    this suite spins up an instance of the Pyramid test app (`pyramid_testapp`)
    """

    def test_splash(self):
        """
        the "splash" page does nothing. hitting means the app set up correctly.
        """
        test_env = self._new_env()
        res = self.testapp.get("/", extra_environ=test_env["extra_environ"])
        self.assertEqual(res.status_code, 200)

    def test_dbSession(self):
        test_env = self._new_env()
        res = self.testapp.get(
            "/tests/dbSession", extra_environ=test_env["extra_environ"]
        )
        self.assertEqual(res.status_code, 200)

    def test_dbSession_callbacks(self):
        test_env = self._new_env()
        res = self.testapp.get(
            "/tests/dbSession/callbacks", extra_environ=test_env["extra_environ"]
        )
        self.assertEqual(res.status_code, 200)


class AppTests_Reader(_AppBackedTests, unittest.TestCase):
    def test_core(self):
        test_env = self._new_env()
        res = self.testapp.get(
            "/tests/dbSession_reader", extra_environ=test_env["extra_environ"]
        )
        self.assertEqual(res.status_code, 200)

    def test_query(self):
        test_env = self._new_env()
        res = self.testapp.get(
            "/tests/dbSession_reader/query", extra_environ=test_env["extra_environ"]
        )
        self.assertEqual(res.status_code, 200)

    def test_query_status(self):
        test_env = self._new_env()
        res = self.testapp.get(
            "/tests/dbSession_reader/query_status",
            extra_environ=test_env["extra_environ"],
        )
        self.assertEqual(res.status_code, 200)


class AppTests_Writer(_AppBackedTests, unittest.TestCase):
    def test_core(self):
        test_env = self._new_env()
        res = self.testapp.get(
            "/tests/dbSession_writer", extra_environ=test_env["extra_environ"]
        )
        self.assertEqual(res.status_code, 200)

    def test_query(self):
        test_env = self._new_env()
        res = self.testapp.get(
            "/tests/dbSession_writer/query", extra_environ=test_env["extra_environ"]
        )
        self.assertEqual(res.status_code, 200)

    def test_query_status(self):
        test_env = self._new_env()
        res = self.testapp.get(
            "/tests/dbSession_writer/query_status",
            extra_environ=test_env["extra_environ"],
        )
        self.assertEqual(res.status_code, 200)


class AppTests_Mixed(_AppBackedTests, unittest.TestCase):
    def test_core(self):
        test_env = self._new_env()
        res = self.testapp.get(
            "/tests/dbSession_mixed", extra_environ=test_env["extra_environ"]
        )
        self.assertEqual(res.status_code, 200)

    def test_query(self):
        test_env = self._new_env()
        res = self.testapp.get(
            "/tests/dbSession_mixed/query", extra_environ=test_env["extra_environ"]
        )
        self.assertEqual(res.status_code, 200)

    def test_query_status(self):
        test_env = self._new_env()
        res = self.testapp.get(
            "/tests/dbSession_mixed/query_status",
            extra_environ=test_env["extra_environ"],
        )
        self.assertEqual(res.status_code, 200)


# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =


class _AppBackedTests_Transaction(object):
    def setUp(self):
        app_test_settings = {"sqlassist.use_zope": True, "sqlassist.is_scoped": True}
        app = pyramid_testapp.main({}, **app_test_settings)
        self.testapp = TestApp(app)

    def _new_env(self):
        test_env = {
            "testapp": self.testapp,
            "extra_environ": {
                "wsgi.url_scheme": "https",
                "HTTP_HOST": "app.example.com",
            },
        }
        return test_env


class AppTestsTransaction_Main(
    _AppBackedTests_Transaction, AppTests_Main, unittest.TestCase
):
    pass


class AppTestsTransaction_Reader(
    _AppBackedTests_Transaction, AppTests_Reader, unittest.TestCase
):
    pass


class AppTestsTransaction_Writer(
    _AppBackedTests_Transaction, AppTests_Writer, unittest.TestCase
):
    pass


class AppTestsTransaction_Mixed(
    _AppBackedTests_Transaction, AppTests_Mixed, unittest.TestCase
):
    pass
