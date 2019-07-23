sqlassist
=========

SqlAssist offers streamlined support handling multiple SqlAlchemy connections under Pyramid.

This package has been working in production environments for several years.

With 0.12.0, there have been some API changes and the introduction of a `pyramid_debugtoolbar` panel

Help / direction is always appreciated.


# WARNING

This package uses scoped sessions by default.

`v0.9.1` introduced a capability to use non-scoped sessions.  This appears to work, but hasn't been tested as thoroughly as I'd like.

non-scoped sessions are not integrated with the `transaction` package, as they are incompatible with Zope's transaction extension. There is probably a way to get this to work, patches welcome.


# Overview

The package facilitates managing multiple SqlAlchemy connections under Pyramid through a single API.  It has been used in Celery too.

There are 4 steps to using this package:

1. It is the job of your Pyramid application's `model` to create SqlAlchemy engines.
2. Each created engine should be passed into `pyramid_sqlassist.initialize_engine`
3. After initializing all the engines, invoke `pyramid_sqlassist.register_request_method` with the name of the request attribute you wish to use
4. SqlAlchemy classes in your model must inherit from `pyramid_sqlassist.DeclaredTable` -- which is just an instance of SqlAlchemy's `declarative_base`


Note: If your Pyramid application connects to the database BEFORE a process fork, you must call `pyramid_sqlassist.reinit_engine(/engine/)`


## What does all this accomplish?

`pyramid_sqlassist` maintains a private Python dict in it's namespace: `_ENGINE_REGISTRY`.  

Calling  `initialize_engine` will wrap each SqlAlchemy engine into a SqlAssist `EngineWrapper` and then register it into the `_ENGINE_REGISTRY`.  The wrapper contains a SqlAlchemy `sessionmaker` created for each engine, along with some convenience functions.

Calling `register_request_method` will invoke Pyramid's `add_request_method` to add a `DbSessionsContainer` onto the Pyramid Request as a specified attribute name.

The `DbSessionsContainer` automatically register a cleanup function via Pyramid's `add_finished_callback` if the database is used.


# Example

This is an example `model.py` for a Pyramid app, which creates a READER and WRITER connection.


    # model.py
	import sqlalchemy
	import pyramid_sqlassist

	from . import model_objects


    def initialize_database(config, settings):

		engine_reader = sqlalchemy.engine_from_config(settings,
													  prefix="sqlalchemy_reader.",
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



# Miscellaneous info

Because Pyramid will lazily create the request database interaction object it is very lightweight.  On initialization, the container will register a cleanup routine via `add_finished_callback`.
	
The `DbSessionsContainer` exposes some methods:

* `reader` - property. memoized access to "reader" connection
* `writer` - property. memoized access to "writer" connection
* `logger` - property. memoized access to "logger" connection
* `any` - property. invokes `get_any()`

* `get_reader` - method. lazy access to "reader" connection
* `get_writer` - method. lazy access to "writer" connection
* `get_logger` - method. lazy access to "logger" connection
* `get_any` - method. tries to find memoized connections. otherwise will invoke a method.

On first access of every "session", the container will re-initialize that session by invoking it as a callable, issuing a `.rollback()`, and stashing the current Pyramid request in the session's `info` dict. 

Within your code, the request can be retrieved via `object_session`

	from sqlalchemy.orm.session import object_session
	_session = object_session(ExampleObject)
	request = _session.info['request']

The cleanup function will call `session.remove()` for all sessions that were used within the request.

A postfork hook is available if needed via `reinit_engine`.  For all managed engines, `engine.dispose()` will be called.

# Why it works:

`DeclaredTable` is simply an instance of `sqlalchemy.ext.declarative.declarative_base`, bound to our own metadata

	# via Pyramid
	# Recommended naming convention used by Alembic, as various different database
	# providers will autogenerate vastly different names making migrations more
	# difficult. See: http://alembic.zzzcomputing.com/en/latest/naming.html
	NAMING_CONVENTION = {
		"ix": 'ix_%(column_0_label)s',
		"uq": "uq_%(table_name)s_%(column_0_name)s",
		"ck": "ck_%(table_name)s_%(constraint_name)s",
		"fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
		"pk": "pk_%(table_name)s"
	}

	# store the metadata in the package (GLOBAL)
	_metadata = sqlalchemy.MetaData(naming_convention=NAMING_CONVENTION)

	# this is used for inheritance only
    DeclaredTable = declarative_base(metadata=_metadata)

Subclassing tables from `DeclaredTable` takes care of all the core ORM setup.

When `initialize_engine` is called, by default `sqlalchemy.orm.configure_mappers` is triggered (this can be deferred to first usage of the ORM, but most people will want to take the performance hit on startup and try to push the mapped tables into shared memory before a fork)


# Misc Objects

## `objects.UtilityObject`

* core object with utility methods for quick prototyping of applications

## `.tools`

* this namepace is currently unused ; it houses some in-progress code for supporting table reflection


# Notes

* PYTHONOPTIMIZE.  all logging functions are nested under `if __debug__:` statements; they can be compiled away during production


# Thanks

Sections of this code were originally taken from or inspired by:

* SqlAlchemy docs
  * Using Thread-Local Scope with Web Applications ( http://docs.sqlalchemy.org/en/rel_0_8/orm/session.html#using-thread-local-scope-with-web-applications )
  * Session Frequently Asked Questions ( http://docs.sqlalchemy.org/en/rel_0_8/orm/session.html#session-frequently-asked-questions )
* Mike Orr's package 'sqlahelper'
* Mike Bayer's blog post 'Django-style Database Routers in SQLAlchemy'
* Pyramid's `@reify` decorator and `set_request_property` attribute
* this was originally based on FindMeOn™'s Pylons based library "opensocialnetwork"


# Example Usage

in your `env.ini`, specify multiple sqlalchemy urls (which might be to different dbs or the same db but with different permissions)

	sqlalchemy_reader.url = postgres://myapp_reader:myapp@localhost/myapp
	sqlalchemy_writer.url = postgres://myapp_writer:myapp@localhost/myapp


/__init__.py:main

	from . import models

    try:
        import uwsgi

        def post_fork_hook():
            models.database_postfork()

        uwsgi.post_fork_hook = post_fork_hook

    except ImportError:
        pass

	def main(global_config, **settings):
		...
		models.initialize_database(settings)
		...


/models/__init__.py

	import sqlassist
	
	ENGINES_ENABLED = ['reader', 'writer', ]

	def initialize_database(settings):

		engine_reader = sqlalchemy.engine_from_config(settings, prefix="sqlalchemy_reader.")
		sqlassist.initialize_engine('reader',engine_reader,default=True, reflect=myapp.models, use_zope=False)

		engine_writer = sqlalchemy.engine_from_config(settings, prefix="sqlalchemy_writer.")
		sqlassist.initialize_engine('writer',engine_writer,default=False, reflect=myapp.models, use_zope=True)

		# custom property: `request.dbSession`
		config.add_request_method(
			request_setup_dbSession,
			'dbSession',
			reify=True,
		)

	def database_postfork():
		for i in ENGINES_ENABLED:
			sqlassist.reinit_engine(i)

	def request_setup_dbSession(request):
		return sqlassist.DbSessionsContainer(request)


/models/actual_models.py

	import sqlalchemy as sa
	from sqlassist import DeclaredTable

	class TestTable(DeclaredTable):
		__tablename__ = 'groups'

		id = sa.Column(sa.Integer, primary_key=True)
		name = sa.Column(sa.Unicode(255), nullable=False)
		description = sa.Column(sa.Text, nullable=False)


in your handlers, you have this ( sqlalchemy is only imported to grab an exception... ):

	import sqlalchemy

	class BaseHandler(object):
		def __init__(self,request):
			self.request = request

	class ViewHandler(BaseHandler):

		def index(self):

			print self.request.dbSession.reader.query(models.actual_models.TestTable).all()

			try:
				#this should fail , assuming reader can't write
				dbTestTable = models.actual_models.TestTable()
				dbTestTable.name= 'Test Case 1'
				self.request.dbSession.reader.add(dbTestTable)
				self.request.dbSession.reader.commit()
	
			except sqlalchemy.exc.ProgrammingError:
				self.request.dbSession.reader.rollback()
				raise ValueError("Commit Failed!")

			#but this should work , assuming writer can write
			dbTestTable = models.actual_models.TestTable()
			dbTestTable.name = 'Test Case 2'
			self.request.dbSession.writer.add(dbTestTable)
			self.request.dbSession.writer.commit()


# UtilityObject

If you inherit from this class, your SqlAlchemy objects have some convenience methods:

* `get__by__id`( self, dbSession, id , id_column='id' ):
* `get__by__column__lower`( self, dbSession, column_name , search , allow_many=False ):
* `get__by__column__similar`( self, dbSession , column_name , seed , prefix_only=True):
* `get__by__column__exact_then_ilike`( self, dbSession, column_name, seed ):
* `get__range`( self, dbSession, start=0, limit=None, sort_direction='asc', order_col=None, order_case_sensitive=True, filters=[], debug_query=False):
* `columns_as_dict`(self):



# Another important note...

## DbSessionsContainer

This convenience class ONLY deals with 3 connections right now :

* reader
* writer
* logger

If you have more/different names - subclass (or create a patch to deal with dynamic names!)  I didn't have time for that.

The reader and writer classes will start with an automatic rollback; The logger will not.


# `transaction` support

By default, the package will try to load the following libraries:

    import transaction
    from zope.sqlalchemy import ZopeTransactionExtension

This can be disabled with an environment variable

	export SQLASSIST_DISABLE_TRANSACTION=1



# Caveats

## $$COMMIT$$

if you're using "Zope" & "transaction" modules :

* you need to call `transaction.commit`
* IMPORTANT remember that `mark_changed` exists!

if you're not using "Zope" & "transaction" modules :

* you need to call "dbSession_writer.commit()"

## Rollbacks

you want to call `rollback` on the specific database sessions to control what is in each one


## catching exceptions if you're trying to support both `transaction.commit()` and `dbsession.commit()`

let's say you do this:

	try:
		dbSession_writer_1.add(object1)
		dbSession_writer_1.commit()
	except AssertionError , e:
		print "Should fail because Zope wants this"

	# add to writer
	dbSession_writer_2.add(object2)

	# commit
	transaction.commit()

in this event, both object1 and object2 will be committed by `transaction.commit()`

You must explicitly invoke a `rollback` after the `AssertionError`


# Reflected Tables

this package once supported trying to handle table reflection.  It is being removed unless someone wants to do a better job.

