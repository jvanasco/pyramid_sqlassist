from __future__ import unicode_literals

# stdlib
import datetime

# pypi
import sqlalchemy

# local
import pyramid_sqlassist
from . import model_objects


# ==============================================================================


def initialize_database(config, settings):
    sqlalchemy_echo = (
        True if (settings.get("sqlalchemy_echo", "").lower() == "true") else False
    )

    # sqlalchemy needs this to be an int.
    for i in ["sqlalchemy", "sqlalchemy_reader", "sqlalchemy_writer"]:
        k = "%s.label_length" % i
        if k in settings:
            settings[k] = int(settings[k])

    use_zope = settings.get("sqlassist.use_zope")
    is_scoped = settings.get("sqlassist.is_scoped")

    engine_reader = sqlalchemy.engine_from_config(
        settings, prefix="sqlalchemy_reader.", echo=sqlalchemy_echo
    )
    pyramid_sqlassist.initialize_engine(
        "reader",
        engine_reader,
        is_default=False,
        model_package=model_objects,
        use_zope=use_zope,
        is_scoped=is_scoped,
    )

    engine_writer = sqlalchemy.engine_from_config(
        settings, prefix="sqlalchemy_writer.", echo=sqlalchemy_echo
    )
    pyramid_sqlassist.initialize_engine(
        "writer",
        engine_writer,
        is_default=False,
        model_package=model_objects,
        use_zope=use_zope,
        is_scoped=is_scoped,
    )
    pyramid_sqlassist.register_request_method(config, "dbSession")

    try:
        model_objects.DeclaredTable.metadata.create_all(engine_reader)
    except Exception as exc:
        print(exc)
    try:
        model_objects.DeclaredTable.metadata.create_all(engine_writer)
    except Exception as exc:
        print(exc)


def insert_initial_records(dbSession):
    _utcnow = datetime.datetime.utcnow()
    _data = (
        (1, 11, 1, "AAAAA", "AAAAA"),
        (2, 12, 2, "aaaaa", "aaaaa"),
        (3, 13, 3, "BBBBB", "Dbbbb"),
        (4, 14, 4, "ccccc", "cDDDD"),
    )
    for _datum in _data:
        f = model_objects.FooObject()
        f.id = _datum[0]
        f.id_alt = _datum[1]
        f.timestamp = _utcnow
        f.status_id = _datum[2]
        f.status = _datum[3]
        f.status_alt = _datum[4]
        dbSession.add(f)
        dbSession.flush()
