import logging

log = logging.getLogger(__name__)

import sqlalchemy
import sqlalchemy.sql
from sqlalchemy.orm import class_mapper as sa_class_mapper
from sqlalchemy.orm.session import object_session

# this is used a bit
func_lower = sqlalchemy.sql.func.lower


# ==============================================================================


class CoreObject(object):
    """Core Database Object class/Mixin"""

    __table_pkey__ = None


class UtilityObject(CoreObject):
    """
    ``UtilityObject`` is a class that provides some common query methods.
    This is intended to simplify app development and debugging by bootstrapping
    some common queries which can be used within `pdb` or simple scrips. The
    functionality provided by this class is best re-written within your app/model
    as there is a bit of overhead in inspecting the object to build the queries
    off of the requisite columns.
    """

    @classmethod
    def get__by__id(cls, dbSession, id, id_column="id"):
        """
        Classmethod.

        Gets an item by an id column named 'id'.  id column can be overriden.

        :param dbSession: The SQLAlchemy ``Session`` to query.
        :param id: The "id" of the object to query. Likely a String or Integer.
        :param id_column: The column hosting the identifier. Default: "id".
        """
        if not hasattr(cls, id_column) and hasattr(cls, "__table_pkey__"):
            id_column = cls.__table_pkey__
        id_col = getattr(cls, id_column)
        if isinstance(id, (list, tuple)):
            return dbSession.query(cls).filter(id_col.in_(id)).all()
        else:
            id_dict = {id_column: id}
            return dbSession.query(cls).filter_by(**id_dict).first()

    @classmethod
    def get__by__column__lower(
        cls, dbSession, column_name, search, allow_many=False, offset=0, limit=None
    ):
        """
        Classmethod.

        Gets items from the database based on a lowercase version of the column.
        useful for situations where you have a function index on a table
        (such as indexing on the lower version of an email addresses)

        :param dbSession: The SQLAlchemy ``Session`` to query.
        :param column_name:
        :param search:
        :param allow_many: default ``False```
        :param offset: default ``0``
        :param limit: default ``None``
        """
        items = (
            dbSession.query(cls)
            .filter(func_lower(getattr(cls, column_name)) == search.lower())
            .offset(offset)
            .limit(limit)
            .all()
        )
        if items:
            if not allow_many:
                if len(items) > 1:
                    raise ValueError(
                        "get__by__column__lower should return 1 and only 1 item"
                    )
                elif len(items) == 1:
                    return items[0]
            else:
                return items
        return None

    @classmethod
    def get__by__column__similar(
        cls, dbSession, column_name, seed, prefix_only=True, offset=0, limit=None
    ):
        """
        Classmethod.

        Searches for a name column entry with the submitted seed prefix.

        :param dbSession: The SQLAlchemy ``Session`` to query.
        :param column_name:
        :param seed:
        :param prefix_only: default ``True```
        :param offset: default ``0``
        :param limit: default ``None``
        """
        query = dbSession.query(cls)
        if prefix_only:
            query = query.filter(
                func_lower(getattr(cls, column_name)).startswith(seed.lower())
            )
        else:
            query = query.filter(
                func_lower(getattr(cls, column_name)).contains(seed.lower())
            )
        results = (
            query.order_by(getattr(cls, column_name).asc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return results

    @classmethod
    def get__by__column__exact_then_ilike(cls, dbSession, column_name, seed):
        """
        Classmethod.

        Searches for an exact match, then case-insensitive version of the
        identified column if no match is found.

        :param dbSession: The SQLAlchemy ``Session`` to query.
        :param column_name:
        :param seed:
        """
        item = dbSession.query(cls).filter(getattr(cls, column_name) == seed).first()
        if not item:
            item = (
                dbSession.query(cls)
                .filter(getattr(cls, column_name).ilike(seed))
                .first()
            )
        return item

    @classmethod
    def get__range(
        cls,
        dbSession,
        offset=0,
        limit=None,
        sort_direction="asc",
        order_col=None,
        order_case_sensitive=True,
        filters=None,
        debug_query=False,
    ):
        """
        Classmethod.

        :param dbSession: The SQLAlchemy ``Session`` to query.
        :param offset: default ``0``
        :param limit: default ``None``
        :param sort_direction: default asc"
        :param order_col: default ``None``
        :param order_case_sensitive: default ``True``
        :param filters: default ``None``
        :param debug_query: default ``False``
        """

        if not order_col:
            order_col = "id"
        query = dbSession.query(cls)
        if filters:
            for _filter in filters:
                query = query.filter(_filter)
        for col in order_col.split(","):
            # declared columns do not have cls.__class__.c
            # reflected columns did in earlier sqlalchemy
            col = getattr(cls, col)
            if sort_direction == "asc":
                if order_case_sensitive:
                    query = query.order_by(col.asc())
                else:
                    query = query.order_by(func_lower(col).asc())
            elif sort_direction == "desc":
                if order_case_sensitive:
                    query = query.order_by(col.desc())
                else:
                    query = query.order_by(func_lower(col).desc())
            else:
                raise ValueError("invalid sort direction")
        query = query.offset(offset).limit(limit)
        results = query.all()
        if __debug__:
            if debug_query:
                log.debug("get__range")
                log.debug(query)
                log.debug(results)
        return results

    def columns_as_dict(self):
        """
        Beware!
        This function will trigger a load of attributes if they have not been
        loaded yet.

        To return only the loaded columns, use ``loaded_columns_as_dict``.
        """
        return dict(
            (col.name, getattr(self, col.name))
            for col in sa_class_mapper(self.__class__).persist_selectable.c
        )

    def loaded_columns_as_dict(self):
        """
        This function will only return the loaded columns as a dict.

        To return ALL columns, potentially triggering the loading of attributes,
        use ``columns_as_dict``.

        See Also: ``loaded_columns_as_list``
        """
        _dict = self.__dict__
        return {
            col.name: _dict[col.name]
            for col in sa_class_mapper(self.__class__).persist_selectable.c
            if col.name in _dict
        }

    def loaded_columns_as_list(self, with_values=False):
        """
        This function will only return the loaded columns as a list.

        By default this returns a list of the keys(columns) only.

        Passing in the argument `with_values=True` will return a list of key(column)/value tuples, which could be blessed into a dict.

        :param with_values: boolean. default ``False``.

        See Also: ``loaded_columns_as_dict``
        """
        _dict = self.__dict__
        if with_values:
            return [
                (col.name, _dict[col.name])
                for col in sa_class_mapper(self.__class__).persist_selectable.c
                if col.name in _dict
            ]
        return [
            col.name
            for col in sa_class_mapper(self.__class__).persist_selectable.c
            if col.name in _dict
        ]

    @property
    def _sqlalchemy_session(self):
        """
        Return the current SQLAlchemy Session for this object.

        This should not be memoized, as an object can be merged across sessions.
        """
        session = object_session(self)
        return session

    @property
    def _pyramid_request(self):
        """
        SQLAssist stashes the active Pyramid ``request`` in the SQLAlchemy
        Session's "info" dict as ``_session.info['request']``.

        This should not be memoized, as an object can be merged across sessions.
        """
        session = object_session(self)
        request = session.info["request"]
        return request


# ==============================================================================


__all__ = ("func_lower", "CoreObject", "UtilityObject")
