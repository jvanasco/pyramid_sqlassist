import logging

log = logging.getLogger(__name__)


# stdlib
import os


# sqlalchemy imports
import sqlalchemy
import sqlalchemy.orm as sqlalchemy_orm
from sqlalchemy.ext.declarative import declarative_base


# use pyramid's reify to memoize
from pyramid.decorator import reify


# transaction support
try:
    # export SQLASSIST_DISABLE_TRANSACTION=1
    SQLASSIST_DISABLE_TRANSACTION = int(
        os.environ.get("SQLASSIST_DISABLE_TRANSACTION", 0)
    )
    if SQLASSIST_DISABLE_TRANSACTION:
        raise ImportError("pyramid_sqlassist: transaction imports disabled")
    import transaction
    from zope.sqlalchemy import register as zope_register
except ImportError as exc:
    transaction = None
    zope_register = None


# # local imports
# from .in_progress import tools


# ==============================================================================


# define an engine registry (GLOBAL)
_ENGINE_REGISTRY = {"!default": None, "engines": {}}


# via pyramid
# Recommended naming convention used by Alembic, as various different database
# providers will autogenerate vastly different names making migrations more
# difficult. See: http://alembic.zzzcomputing.com/en/latest/naming.html
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


# store the metadata in the package (GLOBAL)
_metadata = sqlalchemy.MetaData(naming_convention=NAMING_CONVENTION)


# this is used for inheritance only
DeclaredTable = declarative_base(metadata=_metadata)


class STATUS_CODES(object):
    INIT = 0
    START = 1
    END = 2

    _readable = {INIT: "INIT", START: "START", END: "END"}


# ------------------------------------------------------------------------------


class EngineStatusTracker(object):
    """
    An instance of this class is stashed on each request at init by the `DbSessionsContainer`
    """

    engines = None

    def __init__(self):
        self.engines = {}


# ------------------------------------------------------------------------------


class EngineWrapper(object):
    """
    wraps the SqlAlchemy engine object with convenience functions
    """

    engine_name = None
    sa_engine = None
    sa_sessionmaker = None
    sa_session = None
    sa_session_scoped = None
    is_scoped = None

    def __init__(self, engine_name, sa_engine=None):
        if __debug__:
            log.debug("EngineWrapper.__init__()")
        self.engine_name = engine_name
        self.sa_engine = sa_engine

    def init_sessionmaker(self, is_scoped, sa_sessionmaker_params, use_zope=None):
        """
        `is_scoped` = boolean
        """
        if __debug__:
            log.debug("EngineWrapper.init_sessionmaker()")
        sa_sessionmaker_params["bind"] = self.sa_engine
        sa_sessionmaker = sqlalchemy_orm.sessionmaker(**sa_sessionmaker_params)
        self.sa_sessionmaker = sa_sessionmaker
        if is_scoped:
            self.is_scoped = True
            self.sa_session_scoped = sqlalchemy_orm.scoped_session(sa_sessionmaker)
            if use_zope:
                zope_register(self.sa_session_scoped)
        else:
            if use_zope:
                raise ValueError("`use_zope=True` requires scoped sessions")
            self.is_scoped = False
            self.sa_session = sa_sessionmaker()

    @property
    def session(self):
        """accessor property for sessions"""
        if self.is_scoped:
            return self.sa_session_scoped
        return self.sa_session

    @property
    def _session_repr(self):
        """private property, only used for logging"""
        if self.is_scoped:
            return str(self.sa_session_scoped)
        return str(self.sa_session)

    def request_start(self, request, dbSessionsContainer, force=False):
        """
        This is called once per engine, per request.
        """
        if __debug__:
            log.debug("EngineWrapper.request_start() | request = %s", id(request))
            log.debug(
                "EngineWrapper.request_start() | %s | %s",
                self.engine_name,
                self._session_repr,
            )

        if (
            dbSessionsContainer._engine_status_tracker.engines[self.engine_name]
            == STATUS_CODES.INIT
        ):
            # reinit the session, this only requires invoking it like a function to modify in-place
            dbSessionsContainer._engine_status_tracker.engines[
                self.engine_name
            ] = STATUS_CODES.START
            if self.is_scoped:
                self.sa_session_scoped()
                self.sa_session_scoped.info["request"] = request
                self.sa_session_scoped.rollback()
            else:
                self.sa_session = self.sa_sessionmaker()
                self.sa_session.info["request"] = request
                self.sa_session.rollback()
                # scoped sessions have a `session_factory`, but normal ones do not
                self.sa_session.session_factory = self.sa_sessionmaker
        else:
            if __debug__:
                log.debug(
                    "EngineWrapper.request_start() | %s | %s || DUPLICATE",
                    self.engine_name,
                    self._session_repr,
                )

    def request_end(self, request, dbSessionsContainer=None):
        """
        This is called once per engine, per request.
        """
        if __debug__:
            log.debug("EngineWrapper.request_end() | request = %s", id(request))
            log.debug(
                "EngineWrapper.request_end() | %s | %s",
                self.engine_name,
                self._session_repr,
            )

        # optional tracking
        if dbSessionsContainer is not None:
            if self.engine_name in dbSessionsContainer._engine_status_tracker.engines:
                if (
                    dbSessionsContainer._engine_status_tracker.engines[self.engine_name]
                    == STATUS_CODES.INIT
                ):
                    # we only initialized the containiner. no need to call the sqlalchemy internals
                    return
                dbSessionsContainer._engine_status_tracker.engines[
                    self.engine_name
                ] = STATUS_CODES.END

        # remove no matter what
        if self.is_scoped:
            self.sa_session_scoped.remove()
        else:
            self.sa_session.close()

    def dispose(self):
        """expose the sqlalchemy engine dispose; needed for fork-like operations"""
        self.sa_engine.dispose()


def reinit_engine(engine_name):
    """
    calls `dispose` on all registered engines, instructing SqlAlchemy to drop the connection pool and begin a new one.
    this is useful as a postfork hook in uwsgi or other frameworks, under which there can be issues with database connections due to forking (threads or processes).

    reference:
         Sqlalchemy Documentation: How do I use engines / connections / sessions with Python multiprocessing, or os.fork()?
             http://docs.sqlalchemy.org/en/latest/faq/connections.html#how-do-i-use-engines-connections-sessions-with-python-multiprocessing-or-os-fork
    """
    if engine_name not in _ENGINE_REGISTRY["engines"]:
        return
    wrapped_engine = _ENGINE_REGISTRY["engines"][engine_name]
    wrapped_engine.sa_engine.dispose()


def initialize_engine(
    engine_name,
    sa_engine,
    is_default=False,
    use_zope=False,
    sa_sessionmaker_params=None,
    is_readonly=False,
    is_scoped=True,
    model_package=None,
    reflect=False,
    is_configure_mappers=True,
    is_autocommit=None,
):
    """
    Wraps each engine in an `EngineWrapper`
    Registers each engine into the `_ENGINE_REGISTRY`

    :params:

    :is_default: bool. default `False`.  used to declare which is the default engine.
    :use_zope: bool. default `False`.  enable to use `zope.sqlalchemy`.
    :sa_sessionmaker_params: dict. passed to sqlalchemy's sessionmaker.
    :is_readonly: bool. default `False`.  if set to true, will optimize engine for readonly access
        `autocommit`=True
        `expire_on_commit`=False
    :is_scoped: bool. default `True`.  controls whether or not sessions are scoped_sessions
    :is_configure_mappers: bool. default `True`.  will call `sqlalchemy.orm.configure_mappers`. useful as a startup hook.

    Not Working:
    :model_package: - pass in the model for inspection
    :reflect: - should we reflect?
    """
    if __debug__:
        log.debug("initialize_engine(%s)", engine_name)
        log.info("Initializing Engine: %s", engine_name)

    # configure the engine around a wrapper
    wrapped_engine = EngineWrapper(engine_name, sa_engine=sa_engine)

    # these are some defaults that i once used for writers
    # loggers would autocommit as true
    # not sure this is needed with zope
    if sa_sessionmaker_params is None:
        sa_sessionmaker_params = {}
    _sa_sessionmaker_params__defaults = {"autoflush": True, "autocommit": False}
    for i in _sa_sessionmaker_params__defaults.keys():
        if i not in sa_sessionmaker_params:
            sa_sessionmaker_params[i] = _sa_sessionmaker_params__defaults[i]

    # prior to v0.13.0 and zope.sqlalchemy==1.2, we would load the
    # ZopeTransactionExtension into `sa_sessionmaker_params["extension"]`
    # in this block.
    # now we do a logic check, and pass `use_zope` into `init_sessionmaker`
    if use_zope:
        if not is_scoped:
            raise ValueError("`zope.sqlalchemy` requires scoped sessions")
        if zope_register is None:
            raise ImportError("`zope.sqlalchemy` was not imported earlier")
        if "extension" in sa_sessionmaker_params:
            raise ValueError(
                """`use_zope=True` is incompatible with `extension` in `sa_sessionmaker_params`"""
            )

    if is_readonly or is_autocommit:
        sa_sessionmaker_params["autocommit"] = True
        sa_sessionmaker_params["expire_on_commit"] = False

    # this initializes the session
    wrapped_engine.init_sessionmaker(
        is_scoped, sa_sessionmaker_params, use_zope=use_zope
    )

    # stash the wrapper
    _ENGINE_REGISTRY["engines"][engine_name] = wrapped_engine
    if is_default:
        _ENGINE_REGISTRY["!default"] = engine_name

    if is_configure_mappers:
        sqlalchemy.orm.configure_mappers()

    # finally, reflect if needed
    if reflect:
        raise NotImplementedError
        # tools.reflect_tables(model_package,
        #                      primary=is_default,
        #                      metadata=_metadata,
        #                      engine_name=engine_name,
        #                      sa_engine=sa_engine,
        #                      )


def get_wrapped_engine(name="!default"):
    """retrieves an engine from the registry"""
    try:
        if name == "!default":
            name = _ENGINE_REGISTRY["!default"]
        return _ENGINE_REGISTRY["engines"][name]
    except KeyError:
        raise RuntimeError("No engine '%s' was configured" % name)


def get_session(engine_name):
    """get_session(engine_name): wraps get_wrapped_engine and returns the sa_session_scoped"""
    session = get_wrapped_engine(engine_name).session
    return session


def request_cleanup(request, dbSessionsContainer=None):
    """
    removes all our sessions from the stash.
    this was a cleanup activity once-upon-a-time
    """
    if __debug__:
        log.debug("request_cleanup()")
    for engine_name in _ENGINE_REGISTRY["engines"].keys():
        _engine = get_wrapped_engine(engine_name)
        _engine.request_end(request, dbSessionsContainer=dbSessionsContainer)


def _ensure_cleanup(request, dbSessionsContainer=None):
    """ensures we have a cleanup action"""
    if request_cleanup not in request.finished_callbacks:
        if dbSessionsContainer is not None:

            def f_cleanup(req):
                request_cleanup(req, dbSessionsContainer=dbSessionsContainer)

            request.add_finished_callback(f_cleanup)
        else:
            request.add_finished_callback(request_cleanup)


class DbSessionsContainer(object):
    """
    DbSessionsContainer is the core API object.

    This is used to store, access and manage sqlalchemy/sqlassist

    -- on __init__, it attaches a sqlassist.cleanup_callback to the request
    -- it creates, inits, and stores database sessions
    -- it provides memoized accessors for the database sessions; everything is lazily handled

    # simply set it up with a request method. REALLY
    config.add_request_method(pyramid_sqlassist.DbSessionsContainer, 'dbSession', reify=True,)

    and example usages:

        establish a connection on demand:
            self.request.dbSession.reader.query(do stuff, yay)

        configure a CachingApi with a potential database reader
            cachingApi = CachingApi(database_reader_fetch = self.request.dbSession.get_reader)

    advice:

        when using db connection, utilize dbSession.reader
        when setting up an object, utilize dbSession.get_reader and memoize the reader connection

    """

    _engine_status_tracker = None

    def __init__(self, request):
        self._request = request

        # build a tracker
        _engine_status_tracker = EngineStatusTracker()
        for engine_name in _ENGINE_REGISTRY["engines"].keys():
            _engine_status_tracker.engines[engine_name] = STATUS_CODES.INIT
        self._engine_status_tracker = _engine_status_tracker
        # register our cleanup
        _ensure_cleanup(request, self)

    def _get_initialized_session(self, engine_name):
        _engine = get_wrapped_engine(engine_name)
        _engine.request_start(self._request, self)
        _session = _engine.session
        return _session

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    @reify
    def reader(self):
        """
        database `reader` session.  memoized accessor.
        """
        _session = self._get_initialized_session("reader")
        return _session

    @reify
    def writer(self):
        """
        database `writer` session.  memoized accessor.
        """
        _session = self._get_initialized_session("writer")
        return _session

    @reify
    def logger(self):
        """
        database `logger` session.  memoized accessor.
        """
        _session = self._get_initialized_session("logger")
        return _session

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def get_reader(self):
        """for lazy operations. function to `get` the `reader`."""
        return self.reader

    def get_writer(self):
        """for lazy operations. function to `get` the `writer`."""
        return self.writer

    def get_logger(self):
        """for lazy operations. function to `get` the `logger`."""
        return self.logger

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    # logger is not used as a default preference
    any_preferences = ["reader", "writer"]

    @property
    def any(self):
        """
        get any of the standard database handles in `any_preferences` (default: reader, writer)
        this is a `@property` convenience interface to `.get_any()`
        """
        return self.get_any()

    def get_any(self):
        """
        get any of the standard database handles in `any_preferences` (default: reader, writer)

        this will first try the properties memoized by Pyramid's `@reify` before invoking other attemps
        """
        # keep a list of what we've tried
        _tried = []

        # try the memoized properties first
        _as_dict = self.__dict__
        for _engine_name in self.any_preferences:
            if _engine_name in _as_dict:
                _tried.append(_engine_name)
                return _as_dict[_engine_name]
        # invoke them next
        for _engine_name in self.any_preferences:
            if _engine_name not in _tried:
                return getattr(self, _engine_name)

        raise ValueError("No session available.")


def register_request_method(
    config, request_method_name, dbContainerClass=DbSessionsContainer
):
    """
    ``register_request_method`` invokes Pyramid's ``add_request_method`` and
    stashes some information to enable debugtoolbar support.

    usage:

        def initialize_database(config, settings, is_scoped=None):
            engine_reader = sqlalchemy.engine_from_config(settings, prefix="sqlalchemy_reader.")
            pyramid_sqlassist.initialize_engine('reader', engine_reader)
            pyramid_sqlassist.register_request_method(config, 'dbSession')

    args:
        :config object: Pyramid config object
        :request_method_name string: name to be registered as Pyramid request attribute
        :dbContainerClass class: class to be registered for Pyramid request attribute. default `DbSessionsContainer`
    """
    config.registry.pyramid_sqlassist = {"request_method_name": request_method_name}
    config.add_request_method(dbContainerClass, request_method_name, reify=True)


# ==============================================================================

__all__ = (
    "SQLASSIST_DISABLE_TRANSACTION",
    "_ENGINE_REGISTRY",
    "NAMING_CONVENTION",
    "_metadata",
    "DeclaredTable",
    "STATUS_CODES",
    "EngineStatusTracker",
    "EngineWrapper",
    "reinit_engine",
    "initialize_engine",
    "get_wrapped_engine",
    "get_session",
    "request_cleanup",
    "_ensure_cleanup",
    "DbSessionsContainer",
    "register_request_method",
)
