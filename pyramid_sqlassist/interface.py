import logging
log = logging.getLogger(__name__)


## sqlalchemy imports
import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
import sqlalchemy.orm as sqlalchemy_orm


## transaction support
try:
   import transaction
   from zope.sqlalchemy import ZopeTransactionExtension
except ImportError:
   ZopeTransactionExtension= None
   transaction= None


## local imports
from . import tools



## store the metadata in the package
__metadata= sqlalchemy.MetaData()

# define an engine registry
__engine_registry= { '!default':None , 'engines':{} }

# this is used for inheritance only
DeclaredTable= declarative_base()


class STATUS_CODES:
    STARTED = 1
    ENDED = 2
    

class PyramidSqlassistStatus(object):
    engines = None
    def __init__(self):
        self.engines = {}


class EngineWrapper( object ):
    """wraps the SA engine object with mindless kruft"""

    engine_name = None
    sa_engine = None
    sa_scoped_session = None
    
    def __init__( self, engine_name , sa_engine=None ):
        if __debug__ :
            log.debug("sqlassist#EngineWrapper.__init__()" )
        self.engine_name = engine_name
        self.sa_engine = sa_engine
        self.request = None


    def init_session( self , sa_sessionmaker_params ):
        if __debug__ :
            log.debug("sqlassist#EngineWrapper.init_session()" )
        sa_sessionmaker = sqlalchemy_orm.sessionmaker( **sa_sessionmaker_params )
        self.sa_scoped_session= sqlalchemy_orm.scoped_session( sa_sessionmaker )



    def request_start( self , request , force=False ):
        if __debug__ :
            log.debug("sqlassist#EngineWrapper.request_start() | request = %s" , id(request) )
            log.debug("sqlassist#EngineWrapper.request_start() | %s | %s" , self.engine_name , str(self.sa_scoped_session) )
            
        if not hasattr( request , '_pyramid_sqlassist_status' ):
            request._pyramid_sqlassist_status = PyramidSqlassistStatus()
            
        if self.engine_name not in request._pyramid_sqlassist_status.engines :
            self.sa_scoped_session()

            request._pyramid_sqlassist_status.engines[self.engine_name] = STATUS_CODES.STARTED
        else :
            log.debug("sqlassist#EngineWrapper.request_start() | %s | %s || DUPLICATE" , self.engine_name , str(self.sa_scoped_session) )

        
    def request_end(self,request):
        if __debug__ :
            log.debug("sqlassist#EngineWrapper.request_end() | request = %s" , id(request) )
            log.debug("sqlassist#EngineWrapper.request_end() | %s | %s" , self.engine_name , str(self.sa_scoped_session) )

        if not hasattr( request , '_pyramid_sqlassist_status' ):
            request._pyramid_sqlassist_status = PyramidSqlassistStatus()

        # remove no matter what            
        self.sa_scoped_session.remove()

        if self.engine_name in request._pyramid_sqlassist_status.engines :
            request._pyramid_sqlassist_status.engines[self.engine_name] = STATUS_CODES.ENDED




def init_engine( engine_name , sa_engine , default=False , reflect=False , use_zope=False , sa_sessionmaker_params=None ):
    """
    Creates new engines in the meta object and init the tables for each package
    """
    if __debug__ :
        log.debug("sqlassist#init_engine()" )
        log.info("Initializing Engine : %s" % (engine_name) )

    # configure the engine around a wrapper
    wrapped_engine = EngineWrapper( engine_name , sa_engine=sa_engine )

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

    wrapped_engine.init_session(sa_sessionmaker_params)

    # stash the wrapper
    __engine_registry['engines'][engine_name]= wrapped_engine
    if default:
        __engine_registry[default]= engine_name

    # finally, reflect if needed
    if reflect:
        tools.reflect_tables( reflect , primary=default , metadata=__metadata , engine_name=engine_name , sa_engine=sa_engine )



def get_engine(name='!default'):
    """retrieves an engine from the registry"""
    try:
        if name == '!default':
            name = __engine_registry['!default']
        return __engine_registry['engines'][name]
    except KeyError:
        raise RuntimeError("No engine '%s' was configured" % name)


 

def _ensure_cleanup(request):
    """ensures we have a cleanup action"""
    if dbSessionCleanup not in request.finished_callbacks :
        request.add_finished_callback(dbSessionCleanup)



def dbSession( engine_name ):
    """dbSession(engine_name): wraps get_engine and returns the sa_scoped_session"""
    session = get_engine(engine_name).sa_scoped_session
    return session



def dbSessionSetup(request):
    """The registry is *optionally*
    called upon explicitly to create
    a Session local to the thread and/or request
    """
    if __debug__ :
        log.debug("sqlassist#dbSessionSetup()" )
    if hasattr( request , 'pyramid_sqlassist-dbSessionSetup' ):
        return
    if not hasattr( request , '_pyramid_sqlassist_status' ):
        request._pyramid_sqlassist_status = PyramidSqlassistStatus()
    for engine_name in __engine_registry['engines'].keys():
        _engine= get_engine(engine_name)
        _engine.request_start(request)
    _ensure_cleanup(request)



def dbSessionCleanup(request):
    """
        removes all our sessions from the stash.
        this was a cleanup activity once-upon-a-time
    """
    if __debug__ :
        log.debug("sqlassist#dbSessionCleanup()" )
    for engine_name in __engine_registry['engines'].keys():
        _engine= get_engine(engine_name)
        _engine.request_end(request)
       



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
        ## 
        dbSessionSetup(request)
        ## make sure we cleanup everything!
        _ensure_cleanup(request)


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


