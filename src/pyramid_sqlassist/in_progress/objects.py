import logging

log = logging.getLogger(__name__)

from pyramid_sqlassist.objects import UtilityObject


# ==============================================================================


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


# ==============================================================================


__all__ = ("ReflectedTable",)
