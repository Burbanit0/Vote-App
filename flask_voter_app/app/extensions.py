from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

import os

_STORAGE_URI = os.environ.get('REDIS_URL') or 'memory://'

sim_limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=_STORAGE_URI,
    default_limits=[],
)


def init_simulation_limiter(app: Flask) -> None:
    sim_limiter.init_app(app)
