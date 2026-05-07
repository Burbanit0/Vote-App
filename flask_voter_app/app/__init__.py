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
redis_client = redis.StrictRedis.from_url("redis://redis:6379")


def create_app(config_object="config.Config"):
    app = Flask(__name__)
    app.config.from_object(config_object)
    bcrypt.init_app(app)
    jwt.init_app(app)
    CORS(
        app,
        resources={
            r"/*": {
                "origins": "*",
                "supports_credentials": True,
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization"],
            }
        },
    )

    @app.before_request
    def handle_options():
        if request.method == "OPTIONS":
            response = app.make_default_options_response()
            headers = response.headers
            headers["Access-Control-Allow-Origin"] = "http://localhost:3000"
            headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            return response

    db.init_app(app)
    migrate.init_app(app, db)

    with app.app_context():
        db.create_all()

    from .routes import users, simulation_base, simulation_compare, simulation_advanced, scenarios

    app.register_blueprint(users.auth_bp)
    app.register_blueprint(simulation_base.simulation_base_bp)
    app.register_blueprint(simulation_compare.simulation_compare_bp)
    app.register_blueprint(simulation_advanced.simulation_advanced_bp)
    app.register_blueprint(scenarios.scenarios_bp)

    return app
