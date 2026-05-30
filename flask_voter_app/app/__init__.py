import logging
import os
import time

from flask import Flask, g, request
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

    # ── Logging ────────────────────────────────────────────────────────────
    # structlog handles configuration of the root logger. Flask's own logger
    # is routed through it via stdlib handlers (see app/utils/logger.py).
    from .utils.logger import configure_logging
    configure_logging()
    # Keep Flask's logger as a thin shim — code can still use app.logger.* but
    # everything ends up structured via structlog.
    app.logger.setLevel(logging.INFO)

    # ── Production safety check ────────────────────────────────────────────
    if os.environ.get('FLASK_ENV') == 'production':
        required = ['SECRET_KEY', 'JWT_SECRET_KEY', 'DATABASE_URL']
        missing  = [k for k in required if not os.environ.get(k)]
        if missing:
            raise RuntimeError(
                f"FLASK_ENV=production requires these env vars: {missing}"
            )
        # Also reject default/weak placeholder values
        weak_defaults = {
            'SECRET_KEY':     ('dev-secret-CHANGE-IN-PROD',),
            'JWT_SECRET_KEY': ('dev-jwt-secret-CHANGE-IN-PROD',),
        }
        for var, bad_vals in weak_defaults.items():
            val = os.environ.get(var, '')
            if not val or val in bad_vals:
                raise RuntimeError(
                    f"FLASK_ENV=production requires a strong '{var}' "
                    f"environment variable (current value is missing or a default)."
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
    def set_timing():
        g.start = time.perf_counter()

    @app.before_request
    def handle_options():
        if request.method == "OPTIONS":
            origin       = request.headers.get("Origin", "")
            allow_origin = origin if origin in allowed_origins else allowed_origins[0]
            response     = app.make_default_options_response()
            headers      = response.headers
            headers["Access-Control-Allow-Origin"]      = allow_origin
            headers["Access-Control-Allow-Credentials"] = "true"
            headers["Access-Control-Allow-Methods"]     = "GET, POST, PUT, DELETE, OPTIONS"
            headers["Access-Control-Allow-Headers"]     = "Content-Type, Authorization"
            headers["Access-Control-Max-Age"]           = "3600"
            return response

    # Use structlog for request access logs — JSON in prod, console in dev.
    # Skip /api/health to keep healthcheck noise out of the log stream
    # (uptime monitors poll it every 30s, that's 2 880 noise lines/day).
    from .utils.logger import get_logger
    _access_log = get_logger("app.access")

    @app.after_request
    def log_request(response):
        start = getattr(g, "start", None)
        if start is None or request.path == "/api/health":
            return response
        dur_ms = round((time.perf_counter() - start) * 1000, 1)
        _access_log.info(
            "http.request",
            method=request.method,
            path=request.path,
            status=response.status_code,
            duration_ms=dur_ms,
        )
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
    from .routes.tech       import tech_bp
    from .routes.theory     import theory_bp
    from .routes.health     import health_bp

    app.register_blueprint(users.auth_bp)
    app.register_blueprint(simulation_base.simulation_base_bp)
    # Phase 4.5.a.5: rollback alias at /api/simulations/* matching apiPath('simulations/…')
    # when the frontend falls back to v1 (the v2 router lives on FastAPI at
    # /api/v2/simulations/*). The original /simulations/* prefix stays for the
    # not-yet-migrated sibling blueprints (compare/advanced/whatif/campaign).
    app.register_blueprint(
        simulation_base.simulation_base_bp,
        url_prefix="/api/simulations",
        name="simulation_base_api",
    )
    app.register_blueprint(simulation_compare.simulation_compare_bp)
    # Phase 4.5.a.7: /api/simulations/* rollback alias for the compare blueprint.
    app.register_blueprint(
        simulation_compare.simulation_compare_bp,
        url_prefix="/api/simulations", name="simulation_compare_api",
    )
    app.register_blueprint(simulation_advanced.simulation_advanced_bp)
    app.register_blueprint(scenarios.scenarios_bp)
    app.register_blueprint(simulation_whatif.whatif_bp)
    app.register_blueprint(simulation_campaign.campaign_bp)
    # Phase 4.5.a.6: /api/simulations/* rollback aliases for what-if + campaign
    # (mirror the simulation_base alias above; the v2 routers live on FastAPI).
    app.register_blueprint(
        simulation_whatif.whatif_bp,
        url_prefix="/api/simulations", name="simulation_whatif_api",
    )
    app.register_blueprint(
        simulation_campaign.campaign_bp,
        url_prefix="/api/simulations", name="simulation_campaign_api",
    )
    app.register_blueprint(api_public_bp)
    app.register_blueprint(gallery_bp)
    app.register_blueprint(export_bp)
    app.register_blueprint(election_bp)
    app.register_blueprint(tech_bp)
    app.register_blueprint(theory_bp)
    app.register_blueprint(health_bp)

    # ── Rate limiters ───────────────────────────────────────────────────────
    from .extensions import init_simulation_limiter

    init_api_limiter(app)
    init_simulation_limiter(app)

    # Initialise the auth-bp limiter (Flask-Limiter docs recommend
    # init_app even for module-level instances used via decorators).
    app.config.setdefault("RATELIMIT_ENABLED", True)
    from .routes.users import _limiter as _auth_limiter

    _auth_limiter.init_app(app)

    # ── Generate openapi.json at startup ────────────────────────────────────
    openapi_path = os.path.join(os.path.dirname(__file__), "..", "openapi.json")
    try:
        write_openapi_json(os.path.abspath(openapi_path))
    except OSError:
        pass

    return app
