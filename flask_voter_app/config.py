import os
from datetime import timedelta


class Config:
    """Base configuration — all secrets come from environment variables."""

    # ── Security ──────────────────────────────────────────────────────────────
    # NEVER commit real values. Use .env (gitignored) or platform secrets.
    SECRET_KEY     = os.environ.get('SECRET_KEY',     'dev-secret-CHANGE-IN-PROD')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'dev-jwt-secret-CHANGE-IN-PROD')

    # ── Database ──────────────────────────────────────────────────────────────
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'postgresql://myuser:mypassword@db:5432/mydatabase',
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── JWT ───────────────────────────────────────────────────────────────────
    JWT_ACCESS_TOKEN_EXPIRES  = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_TOKEN_LOCATION         = ['headers']
    JWT_HEADER_NAME            = 'Authorization'
    JWT_HEADER_TYPE            = 'Bearer'
    JWT_ERROR_MESSAGE_KEY      = 'message'
    JWT_JSON_KEY               = 'access_token'

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://redis:6379')

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Comma-separated list of allowed origins, e.g.:
    #   CORS_ORIGINS=https://votelab.vercel.app,https://votelab.app
    CORS_ORIGINS = [
        o.strip()
        for o in os.environ.get('CORS_ORIGINS', 'http://localhost:3000').split(',')
        if o.strip()
    ]

    # ── Debug ─────────────────────────────────────────────────────────────────
    DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    JWT_VERIFY_SUB = False


class ProductionConfig(Config):
    """Production configuration.

    Validation of required secrets is handled in create_app()
    (app/__init__.py) so it actually runs on every startup.
    """

    DEBUG = False
