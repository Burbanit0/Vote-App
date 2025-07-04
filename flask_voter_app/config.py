import os
from datetime import timedelta


class Config:
    """Base configuration class."""

    # Secret key for securing sessions and cookies
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_default_secret_key'

    # Database configuration
    SQLALCHEMY_DATABASE_URI = \
        'postgresql://myuser:mypassword@db:5432/mydatabase'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT Configuration
    # Should be different from SECRET_KEY
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-jwt-secret-key-here')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)  # Token expiration time
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)  # Refresh token
    JWT_TOKEN_LOCATION = ['headers', 'cookies']  # Where to look for tokens
    JWT_COOKIE_SECURE = True  # Only send cookies over HTTPS
    JWT_COOKIE_CSRF_PROTECT = True  # Enable CSRF protection for cookies
    JWT_SESSION_COOKIE = False  # Don't use session cookies
    JWT_COOKIE_SAMESITE = 'lax'  # Cookie SameSite attribute
    JWT_COOKIE_ACCESS_TOKEN = 'access_token_cookie'  # Cookie name
    JWT_COOKIE_REFRESH_TOKEN = 'refresh_token_cookie'  # Cookie name
    JWT_ERROR_MESSAGE_KEY = 'message'  # Key for error messages in responses
    JWT_JSON_KEY = 'access_token'  # Key for the JWT in JSON responses
    JWT_HEADER_NAME = 'Authorization'  # Header name for tokens
    JWT_HEADER_TYPE = 'Bearer'  # Header type for tokens

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
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_default_secret_key'
    JWT_VERIFY_SUB = False


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = \
        'postgresql://username:password@localhost:5432/mydatabase'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
