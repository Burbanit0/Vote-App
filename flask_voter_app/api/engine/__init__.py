"""
api.engine — the framework-neutral compute layer (Phase 4.5.b).

Holds the pure simulation engine relocated out of the Flask `app/` package as
Flask is retired: voting methods, metrics, population generation, constants,
etc. Nothing here imports Flask or FastAPI.
"""
