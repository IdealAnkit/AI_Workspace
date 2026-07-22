"""
ORM declarative base and shared metadata.

All SQLAlchemy models must inherit from Base defined here.
This module is imported by Alembic's env.py for autogeneration.

Usage:
    from app.database.base import Base

    class User(Base):
        __tablename__ = "users"
        ...
"""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Naming convention for Alembic constraint autogeneration
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """
    Declarative base for all ORM models.

    Includes a naming convention so Alembic can autogenerate
    constraint names consistently across all databases.
    """

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
