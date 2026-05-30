"""
app.constants — shim re-exporting the relocated engine constants.

The canonical definitions now live in api_v2/engine/constants.py (Phase 4.5.b).
This shim keeps the legacy `from app.constants import ...` paths working until
the Flask `app/` package is removed in 4.5.b.3.
"""
from api_v2.engine.constants import (  # noqa: F401
    DEFAULT_ISSUES,
    ECONOMY_ISSUES,
    ENV_ISSUES,
    SOCIAL_ISSUES,
)
