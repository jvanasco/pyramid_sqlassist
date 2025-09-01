# stdlib
import datetime
from typing import Optional

# pypi
import sqlalchemy
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

# local
from pyramid_sqlassist import DeclaredTable
from pyramid_sqlassist import UtilityObject


# ==============================================================================


class FooObject(DeclaredTable, UtilityObject):
    __tablename__ = "foo_object"

    id: Mapped[int] = mapped_column(sqlalchemy.Integer, primary_key=True)
    id_alt: Mapped[int] = mapped_column(sqlalchemy.Integer, nullable=False)
    timestamp: Mapped[datetime.datetime] = mapped_column(
        sqlalchemy.DateTime, nullable=False
    )
    status_id: Mapped[Optional[int]] = mapped_column(
        sqlalchemy.Integer, nullable=True, default=None
    )
    status: Mapped[Optional[str]] = mapped_column(
        sqlalchemy.Unicode, nullable=True, default=None
    )
    status_alt: Mapped[Optional[str]] = mapped_column(
        sqlalchemy.Unicode, nullable=True, default=None
    )
