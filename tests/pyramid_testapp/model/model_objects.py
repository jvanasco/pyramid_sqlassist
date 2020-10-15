# pypi
import sqlalchemy

# local
from pyramid_sqlassist import DeclaredTable, UtilityObject


# ==============================================================================


class FooObject(DeclaredTable, UtilityObject):
    __tablename__ = "foo_object"

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    id_alt = sqlalchemy.Column(sqlalchemy.Integer, nullable=False)
    timestamp = sqlalchemy.Column(sqlalchemy.DateTime, nullable=False)
    status_id = sqlalchemy.Column(sqlalchemy.Integer, nullable=True, default=None)
    status = sqlalchemy.Column(sqlalchemy.Unicode, nullable=True, default=None)
    status_alt = sqlalchemy.Column(sqlalchemy.Unicode, nullable=True, default=None)
