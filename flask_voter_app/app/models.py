import datetime
from enum import Enum as PyEnum
from . import db
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime,
    Text,
    Enum,
    Boolean,
    func,
)
from sqlalchemy.orm import relationship

bcrypt = Bcrypt()
jwt = JWTManager()


# Define possible roles in an election
class ElectionRole(PyEnum):
    VOTER = "voter"
    CANDIDATE = "candidate"
    ORGANIZER = "organizer"


election_role_enum = Enum(ElectionRole, name="electionrole")


# Junction table for users and elections with their roles
user_election_roles = db.Table(
    "user_election_roles",
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("election_id", Integer, ForeignKey("elections.id"), primary_key=True),
    Column("role", election_role_enum, nullable=False),
    Column("has_voted", Boolean, default=False, nullable=False),
    Column("additional_data", Text, nullable=True),  # For role-specific data
)


class User(db.Model):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    role = Column(String(10), nullable=False)  # 'Admin' or 'User'
    created_at = Column(DateTime, default=func.current_timestamp())

    participation_points = Column(Integer, default=0)

    # Track participation metrics
    elections_participated = Column(Integer, default=0)
    last_participation_date = Column(DateTime, nullable=True)

    # Basic profile information
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    bio = Column(Text, nullable=True)
    profile_picture = Column(String(200), nullable=True)

    # Relationship to party
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=True)
    party = relationship("Party", back_populates="members")

    # Relationship to elections with roles
    election_roles = relationship(
        "Election",
        secondary=user_election_roles,
        back_populates="participants",
        viewonly=True,
    )

    # Add methods to update participation metrics
    def increment_participation(self):
        """Increment the user's participation count"""
        self.elections_participated += 1
        self.last_participation_date = datetime.utcnow()

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)


class Party(db.Model):
    __tablename__ = "parties"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(db.Text, nullable=True)
    founded_date = Column(DateTime)
    logo_url = Column(String(255))

    # Relationship to User (one-to-many)
    members = relationship("User", back_populates="party")

    def __repr__(self):
        return f"<Party {self.name}>"


class Election(db.Model):
    __tablename__ = "elections"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    processed = Column(Boolean, default=False)
    status = Column(String(100), nullable=True)

    # Relationship to participants with roles
    participants = relationship(
        "User",
        secondary=user_election_roles,
        back_populates="election_roles",
        viewonly=True,
    )

    # Relationship to candidates (users with candidate role in this election)
    candidates = relationship(
        "User",
        secondary=user_election_roles,
        primaryjoin=(user_election_roles.c.election_id == id)
        & (user_election_roles.c.role == ElectionRole.CANDIDATE),
        secondaryjoin=user_election_roles.c.user_id == User.id,
        viewonly=True,
    )

    # Relationship to organizers (users with organizer role in this election)
    organizers = relationship(
        "User",
        secondary=user_election_roles,
        primaryjoin=(user_election_roles.c.election_id == id)
        & (user_election_roles.c.role == ElectionRole.ORGANIZER),
        secondaryjoin=user_election_roles.c.user_id == User.id,
        viewonly=True,
    )


class Vote(db.Model):
    __tablename__ = "votes"
    id = Column(Integer, primary_key=True)
    voter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    candidate_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    election_id = Column(Integer, ForeignKey("elections.id"), nullable=False)
    vote_type = Column(String(50), nullable=True)
    cast_at = Column(DateTime, default=func.current_timestamp())
    rank = Column(Integer, nullable=True)
    weight = Column(db.Float, nullable=True)
    rating = Column(Integer, nullable=True)

    # Relationships
    voter = relationship("User", foreign_keys=[voter_id])
    candidate = relationship("User", foreign_keys=[candidate_id])
    election = relationship("Election")


class Result(db.Model):
    __tablename__ = "results"
    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    election_id = Column(Integer, ForeignKey("elections.id"), nullable=False)
    vote_count = Column(Integer, nullable=False)
    vote_type = Column(String(50), nullable=False)

    # Relationships
    candidate = relationship("User")
    election = relationship("Election")


def get_elections_user_has_voted_in(user_id):
    """Get elections where a user has voted"""
    elections = (
        db.session.query(Election)
        .join(user_election_roles, user_election_roles.c.election_id == Election.id)
        .filter(
            user_election_roles.c.user_id == user_id,
            user_election_roles.c.has_voted is True,
        )
        .all()
    )

    return elections


def has_user_voted_in_election(user_id, election_id):
    """Check if a user has voted in a specific election"""
    return db.session.query(
        db.session.query(user_election_roles)
        .filter(
            user_election_roles.c.user_id == user_id,
            user_election_roles.c.election_id == election_id,
            user_election_roles.c.has_voted is True,
        )
        .exists()
    ).scalar()
