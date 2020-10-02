import logging

log = logging.getLogger(__name__)

# standard lib imports
import types

# pypi
import six

# sqlalchemy imports
import sqlalchemy
import sqlalchemy.orm as sqlalchemy_orm

from .objects import ReflectedTable


# ==============================================================================


def reflect_tables(
    model_package, is_primary=False, metadata=None, sa_engine=None, engine_name=None
):
    """this reflects tables via sqlalchemy.

    THIS DOES NOT WORK YET

    recursively goes through the application's model package looking for classes that inherit from ReflectedTable

    `model_package` the package you want to reflect.  pass in a package, not a string

    Good:
        reflect_tables(myapp.models, is_primary=True)

    Bad - this won't work at all:
        reflect_tables('myapp.models', is_primary=True)
    """
    if __debug__:
        log.debug("reflect_tables(%s)", model_package)

    to_reflect = []
    for content in dir(model_package):
        module = getattr(model_package, content)
        if not isinstance(module, types.ModuleType):
            continue
        for module_element in dir(module):
            module_element = getattr(module, module_element)
            if not isinstance(module_element, type):
                continue
            if issubclass(module_element, ReflectedTable):
                to_reflect.append(module_element)

    for _class in to_reflect:
        raise ValueError(
            "ReflectedTable inheritance does not work well right now.  This is still being developed."
        )
        table_name = _class.__tablename__
        if table_name:
            if __debug__:
                log.info("Reflecting: %s (table: %s)", _class, table_name)

            # turn off SQL Query logging in sqlAlchemey for a moment, it's just makes a mess of things
            _level = logging.getLogger("sqlalchemy.engine").getEffectiveLevel()
            if _level < logging.WARN:
                logging.getLogger("sqlalchemy.engine").setLevel(logging.WARN)

            table = sqlalchemy.Table(
                table_name, metadata, autoload=True, autoload_with=sa_engine
            )
            _class.__sa_stash__[engine_name] = table

            _primarykey = _class.__primarykey__
            primarykey = []
            if _primarykey:
                if isinstance(_primarykey, six.string_types):
                    primarykey.append(getattr(table, _primarykey))
                elif isinstance(_primarykey, list):
                    for _column_name in _primarykey:
                        primarykey.append(getattr(table, _column_name))
            if is_primary:
                sqlalchemy_orm.mapper(_class, table)
            else:
                sqlalchemy_orm.mapper(_class, table, non_primary=True)

            # return logging to it's former state
            logging.getLogger("sqlalchemy.engine").setLevel(_level)


# ==============================================================================


__all__ = ("reflect_tables",)
