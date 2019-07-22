from __future__ import print_function


import logging
log = logging.getLogger(__name__)

"""
fake app for tests
"""
# stdlib
# import os
# import pdb

# pyramid
from pyramid.view import view_config

# pypi


# ==============================================================================


class Handler(object):

    def __init__(self, request):
        self.request = request


class Splash(Handler):

    @view_config(route_name="splash", renderer="templates/splash.mako")
    def splash(self):
        return {}
