# stdlib
import logging
import os
from typing import Any
from typing import Callable
from typing import Dict
from typing import Optional
from typing import Type
from typing import TYPE_CHECKING
from typing import Union

# pypi
from pyramid.decorator import reify
import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from typing_extensions import TypedDict

# ==============================================================================

log = logging.getLogger(__name__)

# ``transaction`` (package)` support
# If ``transaction`` support is not desired, set the following environment variable
#   export SQLASSIST_DISABLE_TRANSACTION=1
# otherwise, the library assumes ``transaction`` is desired and will attempt
# to load the package, potentially raising exceptions.
SQLASSIST_DISABLE_TRANSACTION = int(os.environ.get("SQLASSIST_DISABLE_TRANSACTION", 0))
transaction: Optional[Type]
zope_register: Optional[Callable]
if SQLASSIST_DISABLE_TRANSACTION:
    log.info("pyramid_sqlassist: transaction imports disabled")
    transaction = None
    zope_register = None
else:
    import transaction  # type: ignore[no-redef]  # noqa: F401
    from zope.sqlalchemy import register as zope_register  # type: ignore[no-redef]


if TYPE_CHECKING:
    from pyramid.config import Configurator
    from pyramid.request import Request
    from sqlalchemy.engine.base import Engine
    from sqlalchemy.orm.session import Session

    _TYPES_SESSION = Union[Session, scoped_session[Any], None]


# ------------------------------------------------------------------------------


# define an engine registry (GLOBAL)
_ENGINE_REGISTRY_TYPE = TypedDict(
    "_ENGINE_REGISTRY_TYPE",
    {
        "!default": Optional[str],
        "engines": Dict[str, "EngineWrapper"],
    },
)

_ENGINE_REGISTRY: _ENGINE_REGISTRY_TYPE = {"!default": None, "engines": {}}


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

    _readable = {
        INIT: "INIT",
        START: "START",
        END: "END",
    }


# ------------------------------------------------------------------------------


class EngineStatusTracker(object):
    """
    An instance of this class is stashed on each request at init by
    the ``DbSessionsContainer``.
    """

    engines: Dict[str, int]

    def __init__(self):
        self.engines = {}


# ------------------------------------------------------------------------------


class EngineWrapper(object):
    """
    wraps SQLAlchemy's engine object(s) with convenience functions
    """

    engine_name: str
    sa_engine: "Engine"
    sa_sessionmaker: "sessionmaker"
    sa_session: "Session"
    sa_session_scoped: "scoped_session"
    is_scoped: bool

    def __init__(
        self,
        engine_name: str,
        sa_engine: "Engine",
    ):
        if __debug__:
            log.debug("EngineWrapper.__init__()")
        self.engine_name = engine_name
        self.sa_engine = sa_engine

    def init_sessionmaker(
        self,
        is_scoped: bool,
        sa_sessionmaker_params: Dict,
        use_zope: Optional[bool] = None,
    ):
        """
        :param is_scoped: boolean.
        :param sa_sessionmaker_params: dict. Passed as-is to ``sqlalchemy.orm.sessionmaker()``
        :param use_zope: boolean. optional. Default ``None``.
        """
        if __debug__:
            log.debug("EngineWrapper.init_sessionmaker()")
        sa_sessionmaker_params["bind"] = self.sa_engine
        sa_sessionmaker = sessionmaker(**sa_sessionmaker_params)
        self.sa_sessionmaker = sa_sessionmaker
        if is_scoped:
            self.is_scoped = True
            self.sa_session_scoped = scoped_session(sa_sessionmaker)
            if use_zope:
                if zope_register is None:
                    raise ValueError("`zope_register` was not imported")
                if not self.sa_session_scoped:
                    raise ValueError("missing self.sa_session_scoped")
                zope_register(self.sa_session_scoped)
        else:
            if use_zope:
                raise ValueError("`use_zope=True` requires scoped sessions")
            self.is_scoped = False
            self.sa_session = sa_sessionmaker()

    @property
    def session(self) -> "_TYPES_SESSION":
        """accessor property for sessions"""
        if self.is_scoped:
            return self.sa_session_scoped
        return self.sa_session

    @property
    def _session_repr(self) -> str:
        """private property, only used for logging"""
        if self.is_scoped:
            return str(self.sa_session_scoped)
        return str(self.sa_session)

    def request_start(
        self,
        request: "Request",
        dbSessionsContainer: "DbSessionsContainer",
        force: bool = False,
    ) -> None:
        """
        This is called once per engine, per request.

        :param request: The active Pyramid `Request` instance.
        :param dbSessionsContainer: An instance of ``DbSessionsContainer``
        :param force: boolean. optional. Default ``False``.
        """
        if __debug__:
            log.debug("EngineWrapper.request_start() | request = %s", id(request))
            log.debug(
                "EngineWrapper.request_start() | %s | %s",
                self.engine_name,
                self._session_repr,
            )

        _engine_status = dbSessionsContainer._engine_status_tracker.engines.get(
            self.engine_name
        )

        if (_engine_status is not None) and (_engine_status == STATUS_CODES.INIT):
            # reinit the session, this only requires invoking it like a function to modify in-place
            dbSessionsContainer._engine_status_tracker.engines[
                self.engine_name
            ] = STATUS_CODES.START
            if self.is_scoped:
                self.sa_session_scoped()
                # stash the active Pyramid `request` into the SQLAlchemy "info" dict.
                self.sa_session_scoped.info["request"] = request
                self.sa_session_scoped.rollback()
            else:
                self.sa_session = self.sa_sessionmaker()
                # stash the active Pyramid `request` into the SQLAlchemy "info" dict.
                self.sa_session.info["request"] = request
                self.sa_session.rollback()
                # scoped sessions have a `session_factory`, but normal ones do not
                self.sa_session.session_factory = self.sa_sessionmaker  # type: ignore[attr-defined]
        else:
            if __debug__:
                log.debug(
                    "EngineWrapper.request_start() | %s | %s || DUPLICATE",
                    self.engine_name,
                    self._session_repr,
                )

    def request_end(
        self,
        request: "Request",
        dbSessionsContainer: Optional["DbSessionsContainer"] = None,
    ) -> None:
        """
        This is called once per Engine, per Request.

        :param request: The active Pyramid `Request` instance.
        :param dbSessionsContainer: Aan instance of ``DbSessionsContainer``. optional.
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
                    # we only initialized the containiner. no need to call the SQLAlchemy internals
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
        """
        Exposes SQLAlchemy's ``Engine.dispose``;
        needed for fork-like operations.
        """
        self.sa_engine.dispose()


def reinit_engine(engine_name: str) -> None:
    """
    Calls ``dispose`` on all registered engines, instructing SQLAlchemy to drop
    the connection pool and begin a new one.

    This is useful as a "postfork" hook in uwsgi or other frameworks, under which
    there can be issues with database connections due to forking (threads or processes).

    reference:
         SQLAlchemy Documentation: How do I use engines / connections / sessions with Python multiprocessing, or os.fork()?
             http://docs.sqlalchemy.org/en/latest/faq/connections.html#how-do-i-use-engines-connections-sessions-with-python-multiprocessing-or-os-fork
    """
    if engine_name not in _ENGINE_REGISTRY["engines"]:
        return
    wrapped_engine = _ENGINE_REGISTRY["engines"][engine_name]
    wrapped_engine.sa_engine.dispose()


def initialize_engine(
    engine_name: str,
    sa_engine: "Engine",
    is_default: bool = False,
    use_zope: bool = False,
    sa_sessionmaker_params: Optional[Dict] = None,
    is_readonly: bool = False,
    is_scoped: bool = True,
    model_package: Optional[Type] = None,  # DEPRECATED
    reflect: bool = False,  # DEPRECATED
    is_configure_mappers: bool = True,
    is_autocommit: Optional[bool] = None,
) -> None:
    """
    Wraps each engine in an ``EngineWrapper``
    Registers each engine into the ``_ENGINE_REGISTRY``

    :param is_default: boolean. default ``False``.  Used to declare the default engine.
    :param use_zope: boolean. default ``False``.  Enable to use ``zope.sqlalchemy``.
    :param sa_sessionmaker_params: dict. Passed to SQLAlchemy's ``sessionmaker``.
    :param is_readonly: boolean. default ``False``.  If set to ``True``, SQLAssist will
        optimize the SQLAlchemy Engine for "readonly" access with the following
            ``autocommit=True``
            ``expire_on_commit=False``
    :param is_scoped: boolean. default `True`. Controls whether or not sessions
        are scoped_sessions.
    :param is_configure_mappers: boolean. default `True`.  Will call
        `sqlalchemy.orm.configure_mappers`. Useful as a startup hook.

    # NOT WORKING
    :param model_package: package. Pass in the model for inspection. *DEPRECATED*
    :param reflect: boolean.  Should we reflect? *DEPRECATED*
    """
    if __debug__:
        log.debug("initialize_engine(%s)", engine_name)
        log.info("Initializing Engine: %s", engine_name)

    # configure the engine around a wrapper
    wrapped_engine = EngineWrapper(engine_name, sa_engine)

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


def get_wrapped_engine(name: str = "!default") -> "EngineWrapper":
    """
    Retrieves an engine from the registry.

    :param name: string. Name of the wrapped engine to get. Default: `!default`.
    """
    try:
        if name == "!default":
            _name = _ENGINE_REGISTRY["!default"]
            if _name is None:
                raise KeyError()
            name = _name
        return _ENGINE_REGISTRY["engines"][name]
    except KeyError:
        raise RuntimeError("No engine '%s' was configured" % name)


def get_session(engine_name: str) -> "_TYPES_SESSION":
    """
    Wraps get_wrapped_engine and returns the sa_session_scoped

    :param engine_name: string. Name of the wrapped engine to get the ``.session`` from.
    """
    session = get_wrapped_engine(engine_name).session
    return session


def request_cleanup(
    request: "Request",
    dbSessionsContainer: Optional["DbSessionsContainer"] = None,
) -> None:
    """
    Removes all our sessions from the stash.

    This was a cleanup activity once-upon-a-time

    :param request: The active Pyramid `Request` instance.
    :param dbSessionsContainer: An instance of ``DbSessionsContainer``
    """
    if __debug__:
        log.debug("request_cleanup()")
    for engine_name in _ENGINE_REGISTRY["engines"].keys():
        _engine = get_wrapped_engine(engine_name)
        _engine.request_end(request, dbSessionsContainer=dbSessionsContainer)


def _ensure_cleanup(
    request: "Request",
    dbSessionsContainer: Optional["DbSessionsContainer"] = None,
) -> None:
    """
    Ensures we have a cleanup action.

    :param request: The active Pyramid `Request` instance.
    :param dbSessionsContainer: An instance of ``DbSessionsContainer``
    """
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

    This is used to store, access and manage SQLAlchemy/SQLAssist

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

    _engine_status_tracker: "EngineStatusTracker"

    def __init__(self, request: "Request"):
        """
        :param request: The active Pyramid `Request` instance.
        """
        self._request = request

        # build a tracker
        _engine_status_tracker = EngineStatusTracker()
        for engine_name in _ENGINE_REGISTRY["engines"].keys():
            _engine_status_tracker.engines[engine_name] = STATUS_CODES.INIT
        self._engine_status_tracker = _engine_status_tracker
        # register our cleanup
        _ensure_cleanup(request, self)

    def _get_initialized_session(self, engine_name: str) -> "_TYPES_SESSION":
        """
        :param engine_name: string. Name of the wrapped engine.
        """
        _engine = get_wrapped_engine(engine_name)
        _engine.request_start(self._request, self)
        _session = _engine.session
        return _session

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    @reify
    def reader(self) -> "_TYPES_SESSION":
        """
        database `reader` session.  memoized accessor.
        """
        _session = self._get_initialized_session("reader")
        return _session

    @reify
    def writer(self) -> "_TYPES_SESSION":
        """
        database `writer` session.  memoized accessor.
        """
        _session = self._get_initialized_session("writer")
        return _session

    @reify
    def logger(self) -> "_TYPES_SESSION":
        """
        database `logger` session.  memoized accessor.
        """
        _session = self._get_initialized_session("logger")
        return _session

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def get_reader(self) -> "_TYPES_SESSION":
        """for lazy operations. function to "get" the ``reader``."""
        return self.reader

    def get_writer(self) -> "_TYPES_SESSION":
        """for lazy operations. function to "get" the ``writer``."""
        return self.writer

    def get_logger(self) -> "_TYPES_SESSION":
        """for lazy operations. function to "get" the ``logger``."""
        return self.logger

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    # logger is not used as a default preference
    any_preferences = ["reader", "writer"]

    @property
    def any(self):
        """
        Get any of the standard database handles in `any_preferences` (default: reader, writer)
        This is a `@property` convenience interface to `.get_any()`
        """
        return self.get_any()

    def get_any(self) -> "_TYPES_SESSION":
        """
        Get any of the standard database handles in `any_preferences` (default: reader, writer)

        This will first try the properties memoized by Pyramid's `@reify` before invoking other attemps
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
    config: "Configurator",
    request_method_name: str,
    dbContainerClass=DbSessionsContainer,
) -> None:
    """
    ``register_request_method`` invokes Pyramid's ``add_request_method`` and
    stashes some information to enable ``debugtoolbar`` support.

    usage:

        def initialize_database(config, settings, is_scoped=None):
            engine_reader = sqlalchemy.engine_from_config(settings, prefix="sqlalchemy_reader.")
            pyramid_sqlassist.initialize_engine('reader', engine_reader)
            pyramid_sqlassist.register_request_method(config, 'dbSession')

    :param config: object. Pyramid config object
    :param request_method_name: string. name to be registered as Pyramid ``request`` attribute
    :param dbContainerClass: class. class to be registered for Pyramid ``request`` attribute. default ``DbSessionsContainer``
    """
    config.registry.pyramid_sqlassist = {"request_method_name": request_method_name}
    config.add_request_method(dbContainerClass, request_method_name, reify=True)


# ==============================================================================

__all__ = (
    "_ENGINE_REGISTRY",
    "_ensure_cleanup",
    "_metadata",
    "DbSessionsContainer",
    "DeclaredTable",
    "EngineStatusTracker",
    "EngineWrapper",
    "get_session",
    "get_wrapped_engine",
    "initialize_engine",
    "NAMING_CONVENTION",
    "register_request_method",
    "reinit_engine",
    "request_cleanup",
    "SQLASSIST_DISABLE_TRANSACTION",
    "STATUS_CODES",
)
