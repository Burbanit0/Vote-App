"""W6 spike (PLAN_BEYOND_CI): three /api/v2 routes run in Pyodide, in a Web Worker.

`handle(path, body)` does what the FastAPI route does: the request model validates the
body and fills its defaults, the domain worker runs on its `model_dump()`, and the
response model validates the result. Only the transport changes: no FastAPI, no
thread pool, no rate limiter.
"""

import json

from pydantic import ValidationError

from api.domain.election import polarization, stv
from api.domain.tech import _polis_with_candidates_worker
from api.schemas.election import PolarizationResponse, StvResponse
from api.schemas.perturbers import PolarizationRequest, StvRequest
from api.schemas.tech import PolisWithCandidatesRequest, PolisWithCandidatesResponse

ROUTES = {
    "/api/v2/election/stv": (StvRequest, stv, StvResponse),
    "/api/v2/election/polarization": (PolarizationRequest, polarization, PolarizationResponse),
    "/api/v2/tech/polis": (
        PolisWithCandidatesRequest,
        _polis_with_candidates_worker,
        PolisWithCandidatesResponse,
    ),
}


def handle(path: str, body: str) -> tuple[int, str]:
    request_model, worker, response_model = ROUTES[path]
    try:
        request = request_model.model_validate_json(body)
    except ValidationError as e:
        return 422, json.dumps({"detail": json.loads(e.json())})
    out, status = worker(request.model_dump())
    if status != 200:
        return (status if 400 <= status < 500 else 500), json.dumps(
            {"detail": out.get("error", "Internal error")}
        )
    return 200, response_model.model_validate(out).model_dump_json(by_alias=True)
