from __future__ import print_function

# stdlib
import pdb
import unittest

# pypi
from webtest import TestApp

# local
from . import test_pyramid_app


# ==============================================================================


class PyramidTestApp(unittest.TestCase):

    def setUp(self):
        from .test_pyramid_app import main
        app = main({})
        self.testapp = TestApp(app)

    def test_splash(self):
        test_env = {
            'testapp': self.testapp,
            'extra_environ': {'wsgi.url_scheme': 'https',
                                  'HTTP_HOST': 'app.example.com',
                                  },
        }

        # ensure logout, just to be safe
        res = self.testapp.get('/', extra_environ=test_env['extra_environ'])
