import os

from flask import Flask, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_socketio import SocketIO
import redis


db       = SQLAlchemy()
migrate  = Migrate()
jwt      = JWTManager()
bcrypt   = Bcrypt()
socketio = SocketIO()          # initialised in create_app()

redis_client = redis.StrictRedis.from_url(
    os.environ.get('REDIS_URL', 'redis://redis:6379')
)


def create_app(config_object="config.Config"):
    app = Flask(__name__)
    app.config.from_object(config_object)

    # ── Production safety check ────────────────────────────────────────────
    if os.environ.get('FLASK_ENV') == 'production':
        required = ['SECRET_KEY', 'JWT_SECRET_KEY', 'DATABASE_URL']
        missing  = [k for k in required if not os.environ.get(k)]
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
                "origins":              allowed_origins,
                "supports_credentials": True,
                "methods":              ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers":        ["Content-Type", "Authorization"],
            }
        },
    )

    @app.before_request
    def handle_options():
        if request.method == "OPTIONS":
            origin       = request.headers.get("Origin", "")
            allow_origin = origin if origin in allowed_origins else allowed_origins[0]
            response     = app.make_default_options_response()
            headers      = response.headers
            headers["Access-Control-Allow-Origin"]  = allow_origin
            headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            return response

    db.init_app(app)
    migrate.init_app(app, db)

    with app.app_context():
        db.create_all()

    # ── SocketIO event handlers — must import *before* socketio.init_app()
    #    so that @socketio.on() decorators populate self.handlers when
    #    self.server is still None.  Otherwise handlers are registered only
    #    on the first Server instance and silently lost on subsequent
    #    create_app() calls (e.g. during testing).
    from .events import simulation_events  # noqa: F401

    # ── SocketIO (eventlet async_mode) ─────────────────────────────────────
    socketio.init_app(
        app,
        cors_allowed_origins=allowed_origins,
        async_mode="eventlet",
        logger=False,
        engineio_logger=False,
    )

    # ── Blueprints ──────────────────────────────────────────────────────────
    from .routes import (
        users, simulation_base, simulation_compare,
        simulation_advanced, scenarios, simulation_whatif,
        simulation_campaign,
    )
    from .routes.api_public import api_public_bp, write_openapi_json, init_api_limiter
    from .routes.gallery    import gallery_bp
    from .routes.export     import export_bp
    from .routes.election   import election_bp

    app.register_blueprint(users.auth_bp)
    app.register_blueprint(simulation_base.simulation_base_bp)
    app.register_blueprint(simulation_compare.simulation_compare_bp)
    app.register_blueprint(simulation_advanced.simulation_advanced_bp)
    app.register_blueprint(scenarios.scenarios_bp)
    app.register_blueprint(simulation_whatif.whatif_bp)
    app.register_blueprint(simulation_campaign.campaign_bp)
    app.register_blueprint(api_public_bp)
    app.register_blueprint(gallery_bp)
    app.register_blueprint(export_bp)
    app.register_blueprint(election_bp)

    # ── Rate limiters ───────────────────────────────────────────────────────
    from .extensions import init_simulation_limiter

    init_api_limiter(app)
    init_simulation_limiter(app)

    # ── Generate openapi.json at startup ────────────────────────────────────
    openapi_path = os.path.join(os.path.dirname(__file__), "..", "openapi.json")
    try:
        write_openapi_json(os.path.abspath(openapi_path))
    except OSError:
        pass

    return app
