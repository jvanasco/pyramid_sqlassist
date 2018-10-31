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
    __table_pkey__ = None


class UtilityObject(CoreObject):

    def get__by__id(self, dbSession, id, id_column='id'):
        """gets an item by an id column named 'id'.  id column can be overriden"""
        _cls = self.__class__
        if not hasattr(_cls, id_column) and hasattr(self, '__table_pkey__'):
            id_column = self.__table_pkey__
        id_col = getattr(_cls, id_column)
        if isinstance(id, (list, tuple)):
            return dbSession.query(_cls).filter(id_col.in_(id)).all()
        else:
            id_dict = {id_column: id}
            return dbSession.query(_cls).filter_by(**id_dict).first()

    def get__by__column__lower(self, dbSession, column, search, allow_many=False):
        """gets items from the database based on a lowercase version of the column.
        useful for situations where you have a function index on a table
        (such as indexing on the lower version of an email addresses)"""
        _cls = self.__class__
        items = dbSession.query(_cls)\
            .filter(func_lower(getattr(_cls, column)) == search.lower(),
                    )\
            .all()
        if items:
            if not allow_many:
                if len(items) > 1:
                    raise ValueError("get__by__column__lower should return 1 and only 1 item")
                elif len(items) == 1:
                    return items[0]
            else:
                return items
        return None

    def get__by__column__similar(self, dbSession, column, seed, prefix_only=True):
        """seaches for a name column entry with the submitted seed prefix"""
        _cls = self.__class__
        query = dbSession.query(_cls)
        if prefix_only:
            query = query.filter(func_lower(getattr(_cls, column)).startswith(seed.lower()),
                                 )
        else:
            query = query.filter(func_lower(getattr(_cls, column)).contains(seed.lower()),
                                 )
        results = query\
            .order_by(getattr(_cls, column).asc())\
            .all()
        return results

    def get__by__column__exact_then_ilike(self, dbSession, column, seed):
        """ seaches for an exact, then case-insensitive version of the name column"""
        _cls = self.__class__
        item = dbSession.query(_cls).filter(getattr(_cls, column) == seed).first()
        if not item:
            item = dbSession.query(_cls).filter(getattr(_cls, column).ilike(seed)).first()
        return item

    def get__range(self, dbSession, start=0, limit=None, sort_direction='asc', order_col=None, order_case_sensitive=True, filters=[], debug_query=False):
        """gets a range of items"""
        _cls = self.__class__
        if not order_col:
            order_col = 'id'
        query = dbSession.query(_cls)
        for filter in filters:
            query = query.filter(filter)
        for col in order_col.split(','):
            # declared columns do not have self.__class__.c
            # reflected columns did in earlier sqlalchemy
            col = getattr(_cls, col)
            if sort_direction == 'asc':
                if order_case_sensitive:
                    query = query.order_by(col.asc())
                else:
                    query = query.order_by(func_lower(col).asc())
            elif sort_direction == 'desc':
                if order_case_sensitive:
                    query = query.order_by(col.desc())
                else:
                    query = query.order_by(func_lower(col).desc())
            else:
                raise ValueError('invalid sort direction')
        query = query.offset(start).limit(limit)
        results = query.all()
        if __debug__ and debug_query:
            log.debug("get__range")
            log.debug(query)
            log.debug(results)
        return results

    def columns_as_dict(self):
        """
        Beware- this function will trigger a load of attributes if they have not been loaded yet.
        """
        return dict((col.name, getattr(self, col.name))
                    for col
                    in sa_class_mapper(self.__class__).mapped_table.c
                    )

    def loaded_columns_as_dict(self):
        """
        This function will only return the loaded columns as a dict.

        See Also: ``loaded_columns_as_list``
        """
        _dict = self.__dict__
        return {col.name: _dict[col.name]
                for col in sa_class_mapper(self.__class__).mapped_table.c
                if col.name in _dict
                }

    def loaded_columns_as_list(self, with_values=False):
        """
        This function will only return the loaded columns as a list.
        By default this returns a list of the keys(columns) only.
        Passing in the argument `with_values=True` will return a list of key(column)/value tuples, which could be blessed into a dict.

        See Also: ``loaded_columns_as_dict``
        """
        _dict = self.__dict__
        if with_values:
            return [(col.name, _dict[col.name], )
                    for col in sa_class_mapper(self.__class__).mapped_table.c
                    if col.name in _dict
                    ]
        return [col.name
                for col in sa_class_mapper(self.__class__).mapped_table.c
                if col.name in _dict
                ]

    @property
    def _pyramid_request(self):
        """
        pyramid_sqlassist stashes the `request` in `_session.info['request']`
        this should not be memoized,
        """
        session = object_session(self)
        request = session.info['request']
        return request


class ReflectedTable(UtilityObject):
    """Base class for database objects that are mapped to tables by reflection.
       Have your various model classes inherit from this class.
       If class.__tablename__ is defined, it will reflect that table.
       If class.__primarykey__ is defined, it will set that as the primary key.

       Example:
          class Useraccount(ReflectedTable):
              __tablename__ = "useraccount"
    """
    __tablename__ = None
    __primarykey__ = None
    __sa_stash__ = {}


# ==============================================================================


__all__ = ('func_lower',
           'CoreObject',
           'UtilityObject',
           'ReflectedTable',
           )
