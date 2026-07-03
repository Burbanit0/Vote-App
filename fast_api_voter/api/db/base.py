"""api.db.base — the Declarative base for the async data layer."""
from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Standalone SQLAlchemy 2.0 declarative base (no Flask-SQLAlchemy)."""
