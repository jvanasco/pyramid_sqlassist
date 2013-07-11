import logging
log = logging.getLogger(__name__)

## standard lib imports
import types

## sqlalchemy imports
import sqlalchemy
import sqlalchemy.orm as sqlalchemy_orm


def reflect_tables( app_model , primary=False , metadata=None , sa_engine=None , engine_name=None ):
    """this reflects tables via sqlalchemy.  
    
        recursively goes through the application's model package looking for classes that inherit from ReflectedTable

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

