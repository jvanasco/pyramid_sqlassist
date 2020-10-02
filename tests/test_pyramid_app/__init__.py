"""
fake app for tests
"""
import logging

log = logging.getLogger(__name__)

# stdlib

# pyramid
from pyramid.config import Configurator

# pypi

# local
from . import model


# ==============================================================================


class AttribSafeContextObj(object):
    "from Pylons https://github.com/Pylons/pylons/blob/master/pylons/util.py"

    def __getattr__(self, name):
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            log.debug(
                "No attribute called %s found on c object, returning " "empty string",
                name,
            )
            return ""


def main(global_config, **settings):
    """This function returns a Pyramid WSGI application."""
    _setting_defaults = {
        "mako.directories": ".",
        "sqlalchemy_reader.url": "sqlite://",
        "sqlalchemy_writer.url": "sqlite://",
        "sqlassist.use_zope": False,
        "sqlassist.is_scoped": False,
    }
    for (k, v) in _setting_defaults.items():
        if k not in settings:
            log.debug('main: initialize `settings["%s"]` with default `%s`', k, v)
            settings[k] = v

    config = Configurator(settings=settings)

    # libraries for ease
    config.include("pyramid_mako")

    config.add_route("splash", "/")
    config.add_route("test:dbSession", "/tests/dbSession")
    config.add_route("test:dbSession:callbacks", "/tests/dbSession/callbacks")

    config.add_route("test:dbSession_reader", "/tests/dbSession_reader")
    config.add_route("test:dbSession_reader:query", "/tests/dbSession_reader/query")
    config.add_route(
        "test:dbSession_reader:query_status", "/tests/dbSession_reader/query_status"
    )

    config.add_route("test:dbSession_writer", "/tests/dbSession_writer")
    config.add_route("test:dbSession_writer:query", "/tests/dbSession_writer/query")
    config.add_route(
        "test:dbSession_writer:query_status", "/tests/dbSession_writer/query_status"
    )

    config.add_route("test:dbSession_mixed", "/tests/dbSession_mixed")
    config.add_route("test:dbSession_mixed:query", "/tests/dbSession_mixed/query")
    config.add_route(
        "test:dbSession_mixed:query_status", "/tests/dbSession_mixed/query_status"
    )

    # model & views
    config.scan(".views")

    model.initialize_database(config, settings)

    # request methods!
    return config.make_wsgi_app()


if __name__ == "__main__":
    app = main(None)
    # serve(app, host='0.0.0.0', port=6543)
