from flask import Blueprint

# Create a Blueprint for the routes package
routes_bp = Blueprint('routes', __name__)

# Import the Blueprints from the routes module
from .candidates import bp as candidates_bp
from .voters import bp as voters_bp
from .votes import bp as votes_bp

# Register the Blueprints with the routes Blueprint
@routes_bp.record
def record(state):
    app = state.app
    app.register_blueprint(candidates_bp)
    app.register_blueprint(voters_bp)
    app.register_blueprint(votes_bp)
