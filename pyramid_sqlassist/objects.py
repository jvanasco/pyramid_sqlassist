import logging
log = logging.getLogger(__name__)

## standard lib imports
import types


import sqlalchemy.orm as sqlalchemy_orm


class CoreObject(object):
    __table_pkey__ = None



class UtilityObject(CoreObject):

    def get__by__id( self, dbSession, id , id_column='id' ):
        """gets an item by an id column named 'id'.  id column can be overriden"""
        if not hasattr( self.__class__ , id_column ) and hasattr( self, '__table_pkey__' ) :
            id_column= self.__table_pkey__
        id_col= getattr( self.__class__ , id_column )
        if isinstance( id , (types.ListType,types.TupleType) ):
            return dbSession.query(self.__class__).filter( id_col.in_(id) ).all()
        else :
            id_dict= { id_column : id }
            return dbSession.query(self.__class__).filter_by( **id_dict ).first()


    def get__by__column__lower( self, dbSession, column , search , allow_many=False ):
        """gets items from the database based on a lowercase version of the column. 
        useful for situations where you have a function index on a table
        (such as indexing on the lower version of an email addresses)"""
        items= dbSession.query(self.__class__)\
            .filter(\
                sqlalchemy.sql.func.lower( getattr( self.__class__ , column ) ) == search.lower() 
            )\
            .all()
        if items:
            if not allow_many:
                if len(items) > 1 :
                    raise ValueError("get__by__column__lower should return 1 and only 1 item")
                elif len(items) == 1:
                    return items[0]
            else:
                return items
        return None


    def get__by__column__similar( self, dbSession , column , seed , prefix_only=True):
        """seaches for a name column entry with the submitted seed prefix"""
        query = dbSession.query(self.__class__)
        if prefix_only :
            query = query.filter(\
                sqlalchemy.sql.func.lower( getattr( self.__class__ , column ) ).startswith( seed.lower() )
            )
        else :
            query = query.filter(\
                sqlalchemy.sql.func.lower( getattr( self.__class__ , column ) ).contains( seed.lower() )
            )
        results = query\
            .order_by( getattr( self.__class__ , column ).asc() )\
            .all()
        return results
            
            
    def get__by__column__exact_then_ilike( self, dbSession, column, seed ):
        """ seaches for an exact, then case-insensitive version of the name column"""
        item= dbSession.query(self.__class__).filter( getattr( self.__class__ , column ) == seed ).first()
        if not item:
            item= dbSession.query(self.__class__).filter( getattr( self.__class__ , column ).ilike(seed) ).first()
        return item


    def get__range( self, dbSession , start=0, limit=None , sort_direction='asc' , order_col=None , order_case_sensitive=True , filters=[] , debug_query=False):
        """gets a range of items"""
        if not order_col:
            order_col= 'id'
        query= dbSession.query(self.__class__)
        for filter in filters:
            query= query.filter( filter )
        for col in order_col.split(','):
            # declared columns do not have self.__class__.c
            # reflected columns did in earlier sqlalchemy
            col= getattr( self.__class__, col )
            if sort_direction == 'asc':
                if order_case_sensitive:
                    query= query.order_by( col.asc() )
                else:
                    query= query.order_by( sqlalchemy.sql.func.lower( col ).asc() )
            elif sort_direction == 'desc':
                if order_case_sensitive:
                    query= query.order_by( col.desc() )
                else:
                    query= query.order_by( sqlalchemy.sql.func.lower( col ).desc() )
            else:
                raise ValueError('invalid sort direction')
        query= query.offset(start).limit(limit)
        results= query.all()
        if debug_query:
            log.debug(query)
            log.debug(results)
        return results


    def columns_as_dict(self):
        return dict((col.name, getattr(self, col.name)) for col in sqlalchemy_orm.class_mapper(self.__class__).mapped_table.c)



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

