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
            log.debug("No attribute called %s found on c object, returning "
                      "empty string", name)
            return ''


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    if not settings:
        settings = {'mako.directories': '.',
                    'sqlalchemy_reader.url': 'sqlite://',
                    'sqlalchemy_writer.url': 'sqlite://',
                    }
    config = Configurator(settings=settings)

    # libraries for ease
    config.include('pyramid_mako')
    config.add_route("splash", "/")

    # model & views
    config.scan(".views")
    
    model.initialize_database(config, settings)

    # request methods!
    return config.make_wsgi_app()


if __name__ == '__main__':
    app = main(None)
    # serve(app, host='0.0.0.0', port=6543)
