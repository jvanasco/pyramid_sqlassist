sqlassist
~~~~~~~~~

SqlAssist offers experimental support for SqlAlchemy under Pyramid.

Experimental means that it does things you shouldn't necessarily do, and it's a work in progress to automate certain functionalities.

The challenge is to provide for both:
	1. Reflecting Tables ( ie, not authoring a bunch of python class information for dozens of existing database tables )
	2. Supporting multiple database connections ( read, write, log, etc ) for replicated cluster setups
    3. Support for Declared Tables happened in v0.3


Sections of this code are taken from or instpired by:
	- Mike Orr's package 'sqlahelper'
	- Mike Bayer's blog post 'Django-style Database Routers in SQLAlchemy'
	- this was originally based on findmeon's pylons based opensocialnetwork library


TODO
====

1.  -- this is really ugly , it's patched together from a few different projects that work under sqlalchemy .4/.5
	-- this does work in .6/.7, but it doesn't integrate anything new
	fixing

2.  ------- we don't use the new zope transaction stuff, which most of the pyramid app developers seem to like.
	fixed

3.  ------- the way initialization works is wonky.  init_engine calls a bunch of orm.sessionmaker things that should be configurable
	fixed

4.  ------- there are two registries - engine and session. sigh.
	fixed

5.  still playing with reflected tables , both the __sa_stash__ storage and how they're autoloaded

6.  -- there's a bunch of legacy stuff that hasn't been used/integrated.  ie: under pylons i had middleware that would kill all the dbsessions on exit.  the supporting functions are here, but not used
	fixing
	



Usage
=====

in your env.ini you specify multiple sqlalchemy urls, which might be to different dbs , or the same db but with different permissions

	sqlalchemy_reader.url = postgres://myapp_reader:myapp@localhost/myapp
	sqlalchemy_writer.url = postgres://myapp_writer:myapp@localhost/myapp
	

/__init__.py:main
	models.initialize_database(settings)
	

/models/__init__.py

	import sqlassist
	def initialize_database(settings):
		engine_reader = sqlalchemy.engine_from_config(settings, prefix="sqlalchemy_reader.")
		sqlassist.init_engine('reader',engine_reader,default=True,reflect=myapp.models, use_zope=False)
		engine_writer = sqlalchemy.engine_from_config(settings, prefix="sqlalchemy_writer.")
		sqlassist.init_engine('writer',engine_writer,default=False,reflect=myapp.models, use_zope=True)
		
	from actual_models import *


/models/actual_models.py

	from sqlassist import ReflectedTable

	class TestTable(ReflectedTable):
		__tablename__ = "test_table"

	
in your handlers, you have this ( sqlalchemy is only imported to grab that error ):

import myapp.lib.sqlassist as sqlassist
import sqlalchemy

def index(self):
	dbSession_reader = sqlassist.dbSession("reader")
	dbSession_writer = sqlassist.dbSession("writer")


	print dbSession_reader.query(models.actual_models.TestTable).all()

	try:
		#this should fail , assuming reader can't write
		dbTestTable= models.actual_models.TestTable()
		dbTestTable.name= 'Test Case 1'
		dbSession_reader.add(dbTestTable)
		$$COMMIT$$

	except sqlalchemy.exc.ProgrammingError:
		dbSession_reader.rollback()
		print "DENIED!"


	#but this should work , assuming writer can write
	dbTestTable= models.actual_models.TestTable()
	dbTestTable.name= 'Test Case 2'
	dbSession_writer.add(dbTestTable)
	$$COMMIT$$
	
here's the caveats...

$$COMMIT$$
	if you're using zope & transaction modules :
		- you need to call "transaction.commit" 
	if you're not using zope & transaction modules 
		- you need to call "dbession_writer.commit()" 

Rollbacks
	you want to call rollback on the specific dbSessions to control what is in each one

catching errors if you're trying to support both transaction.commit() and dbsession.commit()
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
	you must explicitly call a rollback after the Assertion Error
	

in case you want to use declared tables...

	in your models.py

		from sqlassist import DeclaredTable
		import sqlalchemy as sa
		
		class Group(DeclaredTable):
			__tablename__ = 'groups'
		
			id = sa.Column(sa.Integer, primary_key=True)
			name = sa.Column(sa.Unicode(255), nullable=False)
			description = sa.Column(sa.Text, nullable=False)

	and if you need a setup routine... 

		import sqlassist
		
		dbSession_writer = sqlassist.dbSession("writer")
	
		def callback():
			model = models.TestModel()
			dbSession_writer.add(model)
			dbSession_writer.flush()
			transaction.commit()
		
		sqlassist.initialize_sql('writer',callback)
	
	the initialize_sql wraps a bunch of code for you
