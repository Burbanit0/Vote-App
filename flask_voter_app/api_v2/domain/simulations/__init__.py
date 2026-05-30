"""api_v2.domain.simulations — pure compute workers for /simulations/* (Phase 4.5.b.3).

Relocated from app/routes/simulation_*.py. Flask-free: the Flask blueprints in
app/routes/ now import these workers and stay thin delegates until app/ is deleted.
"""
