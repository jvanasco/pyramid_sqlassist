sqlassist
=========

SqlAssist offers **experimental** support for SqlAlchemy under Pyramid.

Experimental means that it does things you shouldn't necessarily do, and it's a work in progress to automate certain functionalities.

There is no unit testing, no guarantee, no nothing.  The API may change wildly.  This is largely an exercise in getting things done.

Help / Direction is always appreciated


# Current Status

## `interface.dbSessionSetup`

* Only runs once per request.
* Proxies `EngineWrapper.request_start()` which explicitly calls `Session()` for each scoped session ( as recommended by Mike Bayer )
* Can be ensured through `tweens.sqlassist_tween_factory`, or usage of `interface.DbSessionsContainer`
* Ensures a `finished_callback` of `interface.dbSessionCleanup`

## `interface.dbSessionCleanup`

* Proxies `EngineWrapper.request_end()` which explicitly calls `session.remove()` for each scoped session ( as recommended by Mike Bayer )

## `interface.DbSessionsContainer`

* Quick container to proxy access to sessions
* usage ensures proper setup and teardown of scoped sessions
* not necessary if `tweens.sqlassist_tween_factory` is used

## `tweens.sqlassist_tween_factory`

* usage ensures proper setup and teardown of scoped sessions
* not necessary if `interface.DbSessionsContainer` is used
* setting 'pyramid_sqlassist.regex_path_excludes' in your .ini file will allow you to not setup the database on certain paths

## `objects.UtilityObject`

* core object with utility methods for quick prototyping of applications

## `tools`

* this is all testing and bad code






# Goals

The challenge is to provide for both:

1. Reflecting Tables ( ie, not authoring a bunch of python class information for dozens of existing database tables )
2. Supporting multiple database connections ( read, write, log, etc ) for replicated cluster setups
3. Support for Declared Tables happened in v0.3
4. Optimized Connection Handling
5. Having an alternative to Pyramid's automatic transaction handling ( sometimes you want multiple transactions in a request, or to handle these things yourself ; the transaction handling is still provided)

Sections of this code are taken from or inspired by:

* SqlAlchemy docs
** Using Thread-Local Scope with Web Applications ( http://docs.sqlalchemy.org/en/rel_0_8/orm/session.html#using-thread-local-scope-with-web-applications )
** Session Frequently Asked Questions ( http://docs.sqlalchemy.org/en/rel_0_8/orm/session.html#session-frequently-asked-questions )
* Mike Orr's package 'sqlahelper'
* Mike Bayer's blog post 'Django-style Database Routers in SQLAlchemy'
* pyramid's @reify and set_request_property attributes
* this was originally based on findmeon's pylons based opensocialnetwork library




# Other Usage [ possibly out of date ]

in your env.ini you specify multiple sqlalchemy urls, which might be to different dbs , or the same db but with different permissions

	sqlalchemy_reader.url = postgres://myapp_reader:myapp@localhost/myapp
	sqlalchemy_writer.url = postgres://myapp_writer:myapp@localhost/myapp


/__init__.py:main

	models.initialize_database(settings)


/models/__init__.py

	import sqlassist
	def initialize_database(settings):
		engine_reader = sqlalchemy.engine_from_config(settings,
			prefix="sqlalchemy_reader.")
		sqlassist.init_engine('reader',engine_reader,default=True,
			reflect=myapp.models, use_zope=False)
		engine_writer = sqlalchemy.engine_from_config(settings,
			prefix="sqlalchemy_writer.")
		sqlassist.init_engine('writer',engine_writer,default=False,
			reflect=myapp.models, use_zope=True)

	from actual_models import *


/models/actual_models.py

	from sqlassist import DeclaredTable
	import sqlalchemy as sa

	class Group(DeclaredTable):
		__tablename__ = 'groups'

		id = sa.Column(sa.Integer, primary_key=True)
		name = sa.Column(sa.Unicode(255), nullable=False)
		description = sa.Column(sa.Text, nullable=False)



in your handlers, you have this ( sqlalchemy is only imported to grab an exception... ):

	import myapp.lib.sqlassist as sqlassist
	import sqlalchemy

	class BaseHandler(object):
		def __init__(self,request):
			self.request = request
			self.request.dbSession= sqlassist.DbSessionsContainer(self.request)

	class ViewHandler(BaseHandler):

		def index(self):

			print self.request.dbSession.reader.query(models.actual_models.TestTable).all()

			try:
				#this should fail , assuming reader can't write
				dbTestTable= models.actual_models.TestTable()
				dbTestTable.name= 'Test Case 1'
				self.request.dbSession.reader.add(dbTestTable)
				$$COMMIT$$

			except sqlalchemy.exc.ProgrammingError:
				self.request.dbSession.reader.rollback()
				print "DENIED!"

			#but this should work , assuming writer can write
			dbTestTable= models.actual_models.TestTable()
			dbTestTable.name= 'Test Case 2'
			self.request.dbSession.writer.add(dbTestTable)
			$$COMMIT$$


# sqlassist.DbSessionsContainer

allows you to store and manage a sqlassist interface

* on __init__ , it attaches a sqlassist.cleanup_callback to the request
* it creates, inits, and stores a `reader` , `writer` and `logger` Lazy-loaded/memoized database connections
* it provides 'get_' methods for reader and writer, so they can be provided to functions that do lazy setups downstream

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


# UtilityObject

If you inherit from this class, your SqlAlchemy objects have some convenience methods:

	get__by__id( self, dbSession, id , id_column='id' ):
    get__by__column__lower( self, dbSession, column , search , allow_many=False ):
    get__by__column__similar( self, dbSession , column , seed , prefix_only=True):
    get__by__column__exact_then_ilike( self, dbSession, column, seed ):
    get__range( self, dbSession , start=0, limit=None , sort_direction='asc' ,
    	order_col=None , order_case_sensitive=True , filters=[] , debug_query=False):
    columns_as_dict(self)







# Another important note...

## DbSessionsContainer

This convenience class ONLY deals with 3 connections right now :

* reader
* writer
* logger

If you have more/different names - subclass , or create a patch to deal with dynamic names.  I didn't have time for that.

The reader and writer classes will start with an automatic rollback.

The logger will not.

This behavior is not driven by the actual SqlAlchemy configuration-  though yes, it should be.






# Caveats

## $$COMMIT$$

if you're using zope & transaction modules :

* you need to call "transaction.commit"

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



# TODO

1.  -- this is really ugly , it's patched together from a few different projects that work under sqlalchemy .4/.5
	-- this does work in .6/.7, but it doesn't integrate anything new
	fixing

2.  still playing with reflected tables , both the __sa_stash__ storage and how they're autoloaded
