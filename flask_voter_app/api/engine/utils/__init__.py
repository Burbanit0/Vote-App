"""
api.engine.utils — the pure simulation/compute engine (Phase 4.5.b.3).

Relocated wholesale from app/utils/. Voting methods, metrics, population
generation, campaign/contagion dynamics, real-election data, etc. Nothing here
imports Flask or FastAPI. The four Flask-coupled helpers (auth_utils, cache,
decorators, response_utils) stayed behind in app/utils and die with app/ in the
final teardown.
"""
