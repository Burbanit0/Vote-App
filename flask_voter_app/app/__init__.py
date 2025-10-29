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
redis_client = redis.StrictRedis.from_url('redis://redis:6379')


def create_app(config_object='config.Config'):
    app = Flask(__name__)
    app.debug = True
    app.config.from_object(config_object)
    bcrypt.init_app(app)
    jwt.init_app(app)
    CORS(app, resources={r"/*": {"origins": "*", "supports_credentials": True,
                                            "methods": ["GET", "POST",
                                                        "OPTIONS"],
                                            "allow_headers":
                                            ["Content-Type", "Authorization"]}
                         })

    @app.before_request
    def handle_options():
        if request.method == 'OPTIONS':
            response = app.make_default_options_response()
            headers = response.headers
            headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
            headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, ' \
                'DELETE, OPTIONS'
            headers['Access-Control-Allow-Headers'] = 'Content-Type, ' \
                'Authorization'
            return response

    db.init_app(app)

    migrate.init_app(app, db)
    
    with app.app_context():
        db.create_all()  # Create tables

    from .tasks.scheduler import init_scheduler
    init_scheduler(app)

    from .routes import votes, users, \
        simulation, elections, parties
    app.register_blueprint(votes.bp)
    app.register_blueprint(simulation.bp)
    app.register_blueprint(users.auth_bp)
    app.register_blueprint(parties.bp)
    app.register_blueprint(elections.election_bp)

    return app
