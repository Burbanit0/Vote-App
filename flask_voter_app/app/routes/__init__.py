from flask import Blueprint
# Import the Blueprints from the routes module
from .votes import vote_bp as votes_bp
from .elections import election_bp as election_bp
from .parties import party_bp as party_bp
# Create a Blueprint for the routes package
routes_bp = Blueprint('routes', __name__)


# Register the Blueprints with the routes Blueprint
@routes_bp.record
def record(state):
    app = state.app
    app.register_blueprint(votes_bp)
    app.register_blueprint(election_bp)
    app.register_blueprint(party_bp)
