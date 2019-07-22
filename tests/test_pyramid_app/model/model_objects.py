# pypi
import sqlalchemy

# local
from pyramid_sqlassist import DeclaredTable, UtilityObject


# ==============================================================================


class Foo(DeclaredTable, UtilityObject):
    __tablename__ = 'foo'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    timestamp = sqlalchemy.Column(sqlalchemy.DateTime, nullable=False)
    status_id = sqlalchemy.Column(sqlalchemy.Boolean, nullable=True, default=None)
    status = sqlalchemy.Column(sqlalchemy.Unicode, nullable=True, default=None)
