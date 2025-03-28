from . import db
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship

bcrypt = Bcrypt()
jwt = JWTManager()

class Candidate(db.Model):
    __tablename__ = 'candidates'
    id = Column(Integer, primary_key=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)

class Voter(db.Model):
    __tablename__ = 'voters'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    user = relationship("User", back_populates="voter")


class Vote(db.Model):
    __tablename__ = 'votes'
    id = Column(Integer, primary_key=True)
    voter_id = Column(Integer, ForeignKey('voters.id'), nullable=False)
    candidate_id = Column(Integer, ForeignKey('candidates.id'), nullable=False)
    vote_type = Column(String(50), nullable=False)
    rank = Column(Integer, nullable=True)
    weight = Column(db.Float, nullable=True)
    rating = Column(Integer, nullable=True)

class Result(db.Model):
    __tablename__ = 'results'
    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey('candidates.id'), nullable=False)
    vote_count = Column(Integer, nullable=False)
    vote_type = Column(String(50), nullable=False)

class User(db.Model):
    __tablename__ = 'users'
    id = Column(db.Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    role = Column(String(10), nullable=False)
    created_at = Column(DateTime, default=db.func.current_timestamp())
    voter = relationship("Voter", back_populates="user", uselist=False)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)
    
class Election(db.Model):
    __tablename__ = 'elections'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())

# Relationships
    voters = db.relationship('User', secondary='election_voter', backref=db.backref('elections', lazy='dynamic'))
    candidates = db.relationship('Candidate', secondary='election_candidate', backref=db.backref('elections', lazy='dynamic'))

election_voter = db.Table('election_voter',
    Column('election_id', Integer, ForeignKey('elections.id'), primary_key=True),
    Column('voter_id', Integer, ForeignKey('users.id'), primary_key=True)
)

election_candidate = db.Table('election_candidate',
    Column('election_id', Integer, ForeignKey('elections.id'), primary_key=True),
    Column('candidate_id', Integer, ForeignKey('candidates.id'), primary_key=True)
)