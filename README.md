sqlassist
=========

SqlAssist offers **experimental** support for multiple SqlAlchemy connections under Pyramid.

Experimental means that it does things you shouldn't necessarily do, and it's a work in progress to automate certain functionalities.

The `v0.9.0` release is a partial rewrite of the `v0.1.x` version and is somewhat incompatible.

Tweens were deprecated for explicit request methods.

There is no unit testing in this package, as it's been handled in the implementing package.  This package has been working in production environments for several years.

Help / direction is always appreciated.

# WARNING

This package uses scoped sessions by default.

`v0.9.1` introduced a capability to use non-scoped sessions.  This appears to work, but hasn't been tested thoroughly.

non-scoped sessions are not integrated with the `transaction` package, as they are incompatible with the zope transaction extension. there is probably a way to get this to work, patches welcome.


# Overview

The package facilitates managing multiple SqlAlchemy connections under Pyramid through a single API.  It has been used in Celery too.


# How it works:

When you invoke `initialize_engine`, a sqlalchmey `sessionmaker` is created for that engine.  It is wrapped in a `EngineWrapper`, which provides some conveniece methods and tracked in the `_engine_registry`

Sessions are managed by a `DbSessionsContainer` installed on the request.  This takes one line of code.  Really.

	# custom property: `request.dbSession`
	config.add_request_method(sqlassist.DbSessionsContainer, 'dbSession', reify=True, )

Because Pyramid will lazily create this object, it is very lightweight.  On initialization, the container will register a cleanup routine via `add_finished_callback`.
	
The `DbSessionsContainer` exposes some methods:

* `reader` - property. memoized access to "reader" connection
* `writer` - property. memoized access to "writer" connection
* `logger` - property. memoized access to "logger" connection
* `any` - property. invokes `get_any()`

* `get_reader` - method. lazy access to "reader" connection
* `get_writer` - method. lazy access to "writer" connection
* `get_logger` - method. lazy access to "logger" connection
* `get_any` - method. tries to find memoized connections. otherwise will invoke a method.

On first access of every "session", the container will re-initialize that session by invoking it as a callable, issuing a `.rollback()`, and stashing the current pyramid request in the session's `info` dict. 

Within your code, the request can be retrieved via `object_session`

	from sqlalchemy.orm.session import object_session
	_session = object_session(ExampleObject)
	request = _session.info['request']

The cleanup function will call `session.remove()` for all sessions that were used within the request.

A postfork hook is available if needed via `reinit_engine`.  For all managed engines, `engine.dispose()` will be called.


# Misc

## `objects.UtilityObject`

* core object with utility methods for quick prototyping of applications

## `tools`

* this is all testing and bad code


# Notes

* PYTHONOPTIMIZE.  all logging functions are nested under `if __debug__:` statements; they can be compiled away during production


# Thanks

Sections of this code are taken from or inspired by:

* SqlAlchemy docs
** Using Thread-Local Scope with Web Applications ( http://docs.sqlalchemy.org/en/rel_0_8/orm/session.html#using-thread-local-scope-with-web-applications )
** Session Frequently Asked Questions ( http://docs.sqlalchemy.org/en/rel_0_8/orm/session.html#session-frequently-asked-questions )
* Mike Orr's package 'sqlahelper'
* Mike Bayer's blog post 'Django-style Database Routers in SQLAlchemy'
* pyramid's @reify and set_request_property attributes
* this was originally based on findmeon's pylons based opensocialnetwork library


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
* `get__by__column__lower`( self, dbSession, column , search , allow_many=False ):
* `get__by__column__similar`( self, dbSession , column , seed , prefix_only=True):
* `get__by__column__exact_then_ilike`( self, dbSession, column, seed ):
* `get__range`( self, dbSession, start=0, limit=None, sort_direction='asc', order_col=None, order_case_sensitive=True, filters=[], debug_query=False):
* `columns_as_dict`(self):



# Another important note...

## DbSessionsContainer

This convenience class ONLY deals with 3 connections right now :

* reader
* writer
* logger

If you have more/different names - subclass (or create a patch to deal with dynamic names!)  I didn't have time for that.

The reader and writer classes will start with an automatic rollback.

The logger will not.

This behavior is not driven by the actual SqlAlchemy configuration - though yes, it should be.


# `transaction` support

By default, the package will try to load the following libraries:

    import transaction
    from zope.sqlalchemy import ZopeTransactionExtension

This can be disabled with an environment variable

	export SQLASSIST_DISABLE_TRANSACTION=1



# Caveats

## $$COMMIT$$

if you're using zope & transaction modules :

* you need to call "transaction.commit"
* remember that `mark_changed` exists!

if you're not using zope & transaction modules :

* you need to call "dbession_writer.commit()"

## Rollbacks

you want to call rollback on the specific dbSessions to control what is in each one


## catching exceptions if you're trying to support both transaction.commit() and dbsession.commit()

let's say you do this:

	try:
		dbSession_writer_1.add(object1)
		dbSession_writer_1.commit()
	except AssertionError , e:
		print "Should fail because zope wants this"

	# add to writer
	dbSession_writer_2.add(object2)

	# commit
	transaction.commit()

in this event, both object1 and object2 will be committed by transaction.commit()

You must explicitly call a rollback after the Assertion Error


# Reflected Tables

this is disabled right now.  it's totally janky.  someone else can fix it if they want

