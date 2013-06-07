import logging
log = logging.getLogger(__name__)

import types

import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
import sqlalchemy.orm as sqlalchemy_orm

try:
   import transaction
   from zope.sqlalchemy import ZopeTransactionExtension
except ImportError:
   ZopeTransactionExtension= None
   transaction= None




__metadata= sqlalchemy.MetaData()

# define an engine registry
__engine_registry= { '!default':None , 'engines':{} }

# used for inheritance only
DeclaredTable= declarative_base()


class EngineWrapper( object ):
    """wraps the SA engine object with mindless kruft"""

    def __init__( self, engine_name , sa_engine=None , sa_sessionmaker=None , sa_scoped_session=None ):
        if __debug__ :
            log.debug("sqlassist#EngineWrapper.init()" )
        self.engine_name= engine_name
        self.sa_engine= sa_engine
        self.sa_sessionmaker= sa_sessionmaker
        self.sa_sessionmaker_params= None
        self.sa_scoped_session= sa_scoped_session

    def init_session( self , sa_sessionmaker_params ):
        if sa_sessionmaker_params:
            self.sa_sessionmaker_params= sa_sessionmaker_params
        self.sa_sessionmaker= sqlalchemy_orm.sessionmaker( **self.sa_sessionmaker_params )
        self.sa_scoped_session= sqlalchemy_orm.scoped_session( self.sa_sessionmaker )



def get_engine(name='!default'):
    """retrieves an engine from the registry"""
    if __debug__ :
        log.debug("sqlassist#get_engine()" )
    try:
        if name == '!default':
            name = __engine_registry['!default']
        return __engine_registry['engines'][name]
    except KeyError:
        raise RuntimeError("No engine '%s' was configured" % name)



def init_engine( engine_name , sa_engine , default=False , reflect=False , use_zope=False , sa_sessionmaker_params=None ):
    """
    Creates new engines in the meta object and init the tables for each package
    """
    if __debug__ :
        log.debug("sqlassist#init_engine()" )
        log.info("Initializing Engine : %s" % (engine_name) )

    # configure the engine around a wrapper
    wrapped = EngineWrapper( engine_name , sa_engine=sa_engine )

    # these are some defaults that i once used for writers
    # loggers would autocommit as true
    # not sure this is needed with zope
    if sa_sessionmaker_params is None:
        sa_sessionmaker_params= {}
    _sa_sessionmaker_params= { 'autoflush':True, 'autocommit':False , 'bind':sa_engine }
    for i in _sa_sessionmaker_params.keys():
        if i not in sa_sessionmaker_params:
            sa_sessionmaker_params[i]= _sa_sessionmaker_params[i]

    if use_zope:
        if ZopeTransactionExtension is None:
            raise ImportError('ZopeTransactionExtension was not imported earlier')
        if 'extension' in sa_sessionmaker_params:
            raise ValueError('I raise an error when you call init_engine() with `use_zope=True` and an `extension` in sa_sessionmaker_params. Sorry.')
        sa_sessionmaker_params['extension']= ZopeTransactionExtension()

    wrapped.init_session(sa_sessionmaker_params)

    # stash the wrapper
    __engine_registry['engines'][engine_name]= wrapped
    if default:
        __engine_registry['default']= engine_name


    # finally, reflect if needed
    if reflect:
        reflect_tables( reflect , primary=default , metadata=__metadata , engine_name=engine_name , sa_engine=sa_engine )



def dbSession( engine_name ):
    """dbSession(engine_name): wraps get_engine and returns the sa_scoped_session"""
    if __debug__ :
        log.debug("sqlassist#dbSession(%s)" % engine_name )
    session= get_engine(engine_name).sa_scoped_session
    return session


def dbSessionCleanup():
    """
        removes all our sessions from the stash.
        this was a cleanup activity once-upon-a-time
    """
    if __debug__ :
        log.debug("sqlassist#dbSessionCleanup()" )
    for engine_name in __engine_registry['engines'].keys():
        _engine= get_engine(engine_name)
        if __debug__ :
            log.debug( "sqlassist#dbSessionCleanup(%s)" % engine_name )
        _engine.sa_scoped_session.close()



class UtilityObject(object):
    __table_pkey__= None

    def get__by__id( self, dbSession, id , id_column='id' ):
        """gets an item by an id column named 'id'.  id column can be overriden"""
        if not hasattr( self.__class__ , id_column ) and hasattr( self, '__table_pkey__' ) :
            id_column= self.__table_pkey__
        id_col= getattr( self.__class__ , id_column )
        if type(id) == type([]):
            return dbSession.query(self.__class__).filter( id_col.in_(id) ).all()
        else :
            id_dict= { id_column : id }
            return dbSession.query(self.__class__).filter_by( **id_dict ).first()


    def get__by__column__lower( self, dbSession, column , search , allow_many=False ):
        """gets items from the database based on a lowercase version of the column. useful for situations where you have a function index on a table, such as indexing on the lower version of an email addresses."""
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


def reflect_tables( app_model , primary=False , metadata=None , sa_engine=None , engine_name=None ):
    """this reflects tables via sqlalchemy.  recursively goes through the application's model package looking for classes that inherit from ReflectedTable

        app_model- the package you want to reflect.  pass in a package, not a string

        Good:
            reflect_tables( myapp.models , primary=True )

        Bad - this won't work at all:
            reflect_tables( 'myapp.models' , primary=True )

    """
    if __debug__ :
        log.debug("sqlassist#reflect_tables(%s)" , app_model )
    to_reflect = []
    for content in dir( app_model ):
        module = getattr( app_model , content )
        if not isinstance( module , types.ModuleType ):
            continue
        for module_element in dir( module ):
            module_element = getattr( module, module_element )
            if not isinstance( module_element , types.TypeType ):
                continue
            if issubclass( module_element , ReflectedTable ):
                to_reflect.append( module_element )
    for _class in to_reflect:
        raise ValueError('ReflectedTable inheritance does not work well right now.')
        table_name = _class.__tablename__
        if table_name:
            log.info("Reflecting : %s (table: %s)" % (_class , table_name) )

            # turn off SQL Query logging in sqlAlchemey for a moment , it's just makes a mess of things
            _level= logging.getLogger('sqlalchemy.engine').getEffectiveLevel()
            if _level < logging.WARN :
                logging.getLogger('sqlalchemy.engine').setLevel(logging.WARN)

            table= sqlalchemy.Table( table_name, metadata, autoload=True , autoload_with=sa_engine )
            _class.__sa_stash__[engine_name]= table

            _primarykey = _class.__primarykey__
            primarykey= []
            if _primarykey:
                if isinstance( _primarykey, types.StringTypes ):
                    primarykey.append( getattr( table , _primarykey ) )
                elif isinstance( _primarykey, types.ListTypes ):
                    for _column_name in _primarykey :
                        primarykey.append( getattr( table , _column_name ) )
            if primary:
                sqlalchemy_orm.mapper( _class , table )
            else:
                sqlalchemy_orm.mapper( _class , table , non_primary=True )

            # return logging to it's former state
            logging.getLogger('sqlalchemy.engine').setLevel(_level)


#####
#####  playing with reset code
#####


def cleanup_callback(request):
    """request.add_finished_callback(sqlassist.cleanup_callback)"""
    dbSessionCleanup()




class DbSessionsContainer(object):
    """
        DbSessionsContainer allows you to store and manage a sqlassist interface
        
        -- on __init__ , it attaches a sqlassist.cleanup_callback to the request
        -- it creates, inits, and stores a `reader` and `writer` database handle
        -- it provides 'get_' methods for reader and writer, so they can be provided to functions that do lazy setups downstream 
        
        recommended usage is configuring a class-based pyramid view with the following attribute
        
            self.request.dbSession= sqlassist.DbSessionsContainer(self.request)
        
        and example usages:
            
            establish a connection on demand :
                self.request.dbSession.reader.query( do stuff , yay )
                
            configure a CachingApi with a potential database reader 
                cachingApi = CachingApi( database_reader_fetch = self.request.dbSession.get_reader )
                
        rule of thumb:

            when using db connection , utilize dbSession.reader
            when setting up an object , utilize dbSession.get_reader and memoize the reader connection

    """
    _any = None
    _logger= None
    _reader= None
    _writer= None


    def __init__(self,request):
        request.add_finished_callback(cleanup_callback)


    @property
    def any(self):
        if self._any is None :
            self._any = self.get_any()
        return self._any

    def get_any( self ):
        for i in ( self.reader , self.writer ):
            if i is not None:
                return i
        raise ValueError('No dbSession to return')
        

    @property
    def reader(self):
        if self._reader is None :
            self._reader = dbSession("reader")
            self._reader.rollback()
        return self._reader
    
    def get_reader(self):
        return self.reader


    @property
    def writer(self):
        if self._writer is None :
            self._writer = dbSession("writer")
            self._writer.rollback()
        return self._writer
    
    def get_writer(self):
        return self.writer


    @property
    def logger(self):
        if self._logger is None :
            self._logger = dbSession("logger")
        return self._logger
    
    def get_logger(self):
        return self.logger




## or we could do this with tweens...



from pyramid.tweens import EXCVIEW

def includeme(config):
    """set up tweens"""
    return
    config.add_tween('pyramid_sqlassist.sqlassist_tween_factory', under=EXCVIEW)

import re
re_excludes= re.compile("/(img|_debug|js|css)")

def sqlassist_tween_factory(handler, registry):
    def sqlassist_tween(request):
        if re.match( re_excludes , request.path_info ):
            return handler(request)
        try:
            response = handler(request)
            return response
        finally :
            if __debug__ :
                log.debug("sqlassist_tween_factory - dbSessionCleanup()")
            dbSessionCleanup()
    return sqlassist_tween


def initialize_sql(engine_name,population_callback=None,metadata=None):
    if metadata:
        DeclaredTable.metadata= metadata
    _dbSession= dbSession(engine_name)
    _sa_engine= get_engine(engine_name).sa_engine
    _dbSession.configure( bind = _sa_engine  )
    DeclaredTable.metadata.bind = _sa_engine
    DeclaredTable.metadata.create_all(_sa_engine)
    try:
        if population_callback:
            population_callback()
    except IntegrityError:
        transaction.abort()


