import datetime
from . import db
from sqlalchemy import Column, Integer, String, DateTime, Text, func, JSON

from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()


class User(db.Model):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    role = Column(String(10), nullable=False)  # 'Admin' or 'User'
    created_at = Column(DateTime, default=func.current_timestamp())

    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    bio = Column(Text, nullable=True)
    profile_picture = Column(String(200), nullable=True)

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
