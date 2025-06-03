import os


class Config:
    """Base configuration class."""

    # Secret key for securing sessions and cookies
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_default_secret_key'

    # Database configuration
    SQLALCHEMY_DATABASE_URI = \
        'postgresql://myuser:mypassword@db:5432/mydatabase'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    REDIS_URL = 'redis://redis:6379'
    # Flask-CORS configuration
    CORS_HEADERS = 'Content-Type'

    # Other configurations
    DEBUG = os.environ.get('DEBUG') or True


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    # Use in-memory SQLite for testing
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = \
        'postgresql://username:password@localhost:5432/mydatabase'
