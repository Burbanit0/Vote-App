"""
api_v2.db.models — the three persistent models, off Flask-SQLAlchemy.

These mirror app/models.py exactly (same table names, same columns) so they
bind to the existing database with no migration. Key compatibility points
preserved from the Flask era (see [[project-phase4-status]] invariants):

* `hashed_password` is the ATTRIBUTE name (fastapi-users contract) mapped to
  the existing DB column `password_hash`.
* `role` (legacy 'Admin'/'User') is kept alongside the `is_superuser` boolean.
* `email` is the canonical login identifier (NOT NULL UNIQUE).
"""
from __future__ import annotations

import datetime
from typing import Any, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api_v2.db.base import Base


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


class User(Base):
    __tablename__ = "users"

    id:            Mapped[int] = mapped_column(Integer, primary_key=True)
    username:      Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    # Attribute `hashed_password` (fastapi-users), DB column `password_hash`.
    hashed_password: Mapped[str] = mapped_column("password_hash", String(128), nullable=False)
    role:          Mapped[str] = mapped_column(String(10), nullable=False)
    created_at:    Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    first_name:      Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name:       Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    bio:             Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    profile_picture: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    google_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, unique=True)
    github_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, unique=True)
    email:     Mapped[str] = mapped_column(String(120), nullable=False, unique=True)

    is_active:    Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_verified:  Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Convenience alias so legacy code reading `.password_hash` keeps working.
    @property
    def password_hash(self) -> str:
        return self.hashed_password

    @password_hash.setter
    def password_hash(self, value: str) -> None:
        self.hashed_password = value


class SimulationScenario(Base):
    __tablename__ = "simulation_scenarios"

    id:         Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id:    Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    name:       Mapped[str] = mapped_column(String(100), nullable=False)
    config:     Mapped[dict] = mapped_column(JSON, nullable=False)
    results:    Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, default=_utcnow)

    user: Mapped["User"] = relationship("User", backref="simulation_scenarios", lazy="selectin")

    def to_summary(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "config": self.config,
        }

    def to_detail(self) -> dict:
        return {**self.to_summary(), "results": self.results}


class GalleryScenario(Base):
    """Public gallery of interesting simulation scenarios (no auth to read)."""
    __tablename__ = "gallery_scenarios"

    id:          Mapped[int] = mapped_column(Integer, primary_key=True)
    title:       Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    params:          Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    results_summary: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    tags:        Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at:  Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, default=_utcnow)
    views:       Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    def to_dict(self, include_params: bool = False) -> dict:
        data: dict[str, Any] = {
            "id":              self.id,
            "title":           self.title,
            "description":     self.description,
            "tags":            self.tags or [],
            "views":           self.views,
            "is_featured":     self.is_featured,
            "created_at":      self.created_at.isoformat() if self.created_at else None,
            "results_summary": self.results_summary or {},
        }
        if include_params:
            data["params"] = self.params or {}
        return data
