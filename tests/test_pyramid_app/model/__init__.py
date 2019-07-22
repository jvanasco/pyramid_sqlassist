# pypi
import sqlalchemy

# local
import pyramid_sqlassist
from . import model_objects


# ==============================================================================


def initialize_database(config, settings, is_scoped=None):
    sqlalchemy_echo = True if (settings.get('sqlalchemy_echo', '').lower() == 'true') else False

    # sqlalchemy needs this to be an int.
    for i in ['sqlalchemy',
              'sqlalchemy_reader',
              'sqlalchemy_writer',
              ]:
        k = "%s.label_length" % i
        if k in settings:
            settings[k] = int(settings[k])

    engine_reader = sqlalchemy.engine_from_config(settings,
                                                  prefix="sqlalchemy_reader.",
                                                  echo=sqlalchemy_echo,
                                                  )
    pyramid_sqlassist.initialize_engine('reader',
                                        engine_reader,
                                        is_default=False,
                                        model_package=model_objects,
                                        use_zope=False,
                                        is_scoped=is_scoped,
                                        )

    engine_writer = sqlalchemy.engine_from_config(settings,
                                                  prefix="sqlalchemy_writer.",
                                                  echo=sqlalchemy_echo,
                                                  )
    pyramid_sqlassist.initialize_engine('writer',
                                        engine_writer,
                                        is_default=False,
                                        model_package=model_objects,
                                        use_zope=False,
                                        is_scoped=is_scoped,
                                        )
    pyramid_sqlassist.register_request_method(config, 'dbSession')

