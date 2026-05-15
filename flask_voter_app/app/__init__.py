import os

from flask import Flask, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
import redis


db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
bcrypt = Bcrypt()
redis_client = redis.StrictRedis.from_url(
    os.environ.get('REDIS_URL', 'redis://redis:6379')
)


def create_app(config_object="config.Config"):
    app = Flask(__name__)
    app.config.from_object(config_object)

    # ── Production safety check ────────────────────────────────────────────
    if os.environ.get('FLASK_ENV') == 'production':
        required = ['SECRET_KEY', 'JWT_SECRET_KEY', 'DATABASE_URL']
        missing = [k for k in required if not os.environ.get(k)]
        if missing:
            raise RuntimeError(
                f"FLASK_ENV=production requires these env vars: {missing}"
            )

    bcrypt.init_app(app)
    jwt.init_app(app)

    # ── CORS — origins come from config, never wildcard ────────────────────
    allowed_origins = app.config.get('CORS_ORIGINS', ['http://localhost:3000'])

    CORS(
        app,
        resources={
            r"/*": {
                "origins": allowed_origins,
                "supports_credentials": True,
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization"],
            }
        },
    )

    @app.before_request
    def handle_options():
        if request.method == "OPTIONS":
            # Use the first allowed origin for preflight; real browsers send Origin header
            origin = request.headers.get("Origin", "")
            allow_origin = origin if origin in allowed_origins else allowed_origins[0]
            response = app.make_default_options_response()
            headers = response.headers
            headers["Access-Control-Allow-Origin"]  = allow_origin
            headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            return response

    db.init_app(app)
    migrate.init_app(app, db)

    with app.app_context():
        db.create_all()

    from .routes import users, simulation_base, simulation_compare, simulation_advanced, scenarios, simulation_whatif, simulation_campaign
    from .routes.api_public import api_public_bp, write_openapi_json, init_api_limiter

    app.register_blueprint(users.auth_bp)
    app.register_blueprint(simulation_base.simulation_base_bp)
    app.register_blueprint(simulation_compare.simulation_compare_bp)
    app.register_blueprint(simulation_advanced.simulation_advanced_bp)
    app.register_blueprint(scenarios.scenarios_bp)
    app.register_blueprint(simulation_whatif.whatif_bp)
    app.register_blueprint(simulation_campaign.campaign_bp)
    app.register_blueprint(api_public_bp)

    # ── Bind the public-API rate limiter to this app ───────────────────────
    init_api_limiter(app)

    # ── Generate openapi.json at startup ───────────────────────────────────
    openapi_path = os.path.join(os.path.dirname(__file__), "..", "openapi.json")
    try:
        write_openapi_json(os.path.abspath(openapi_path))
    except OSError:
        pass   # non-critical: spec is also served dynamically at /api/v1/openapi.json

    return app
