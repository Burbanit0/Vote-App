import datetime
from . import db
from sqlalchemy import Boolean, Column, Integer, String, ForeignKey, DateTime, Text, func, JSON, cast
from sqlalchemy import true as sa_true, false as sa_false

from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()


class User(db.Model):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    role = Column(String(10), nullable=False)  # legacy 'Admin' / 'User' — see is_superuser below
    created_at = Column(DateTime, default=func.current_timestamp())

    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    bio = Column(Text, nullable=True)
    profile_picture = Column(String(200), nullable=True)

    google_id = Column(String(100), nullable=True, unique=True)
    github_id = Column(String(100), nullable=True, unique=True)
    # Phase 4.3.a: email becomes the canonical login identifier (fastapi-users
    # contract). Legacy username stays for backward compat — see app/routes/users.py.
    email = Column(String(120), nullable=False, unique=True)

    # Phase 4.3.a: fastapi-users user-table contract.
    # `is_superuser` shadows the legacy `role` column ('Admin' → True).
    is_active    = Column(Boolean, nullable=False, server_default=sa_true())
    is_superuser = Column(Boolean, nullable=False, server_default=sa_false())
    is_verified  = Column(Boolean, nullable=False, server_default=sa_true())

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)


class SimulationScenario(db.Model):
    __tablename__ = "simulation_scenarios"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    config = Column(JSON, nullable=False)
    results = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    user = db.relationship("User", backref=db.backref("simulation_scenarios", lazy=True))

    def to_summary(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "config": self.config,
        }

    def to_detail(self) -> dict:
        return {**self.to_summary(), "results": self.results}


class GalleryScenario(db.Model):
    """
    Public gallery of interesting simulation scenarios.

    Accessible without authentication.  Admin sets is_featured=True
    to promote a scenario to the "En vedette" section.
    """
    __tablename__ = "gallery_scenarios"

    id          = Column(Integer, primary_key=True)
    title       = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    params          = Column(JSON, nullable=False, default=dict)
    results_summary = Column(JSON, nullable=False, default=dict)
    tags        = Column(JSON, nullable=False, default=list)   # stored as JSON array
    created_at  = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    views       = Column(Integer, default=0, nullable=False)
    is_featured = Column(Boolean, default=False, nullable=False)

    def to_dict(self, include_params: bool = False) -> dict:
        data: dict = {
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
