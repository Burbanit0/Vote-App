from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

sim_limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="memory://",
    default_limits=[],
)


def init_simulation_limiter(app):
    sim_limiter.init_app(app)
