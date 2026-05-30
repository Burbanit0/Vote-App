"""
app.services.election_service — shim (Phase 4.5.b.3).

ElectionService moved to api_v2/domain/election/election_service.py. This
re-export keeps legacy `from app.services.election_service import ElectionService`
working until app/ is deleted in the final teardown.
"""
from api_v2.domain.election.election_service import ElectionService  # noqa: F401
