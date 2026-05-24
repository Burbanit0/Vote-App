"""
Generate an OpenAPI 3.1 spec from the Pydantic schemas in app/schemas/.

Run:
    cd flask_voter_app
    python scripts/gen_openapi.py
    # writes openapi.gen.json next to the existing openapi.json

This is a standalone JSON spec built directly from Pydantic — independent
of Flask-OpenAPI3's auto-generated openapi.json (which lives at the Flask
app level and reflects whatever endpoints are wired).

The frontend (voter-app) consumes openapi.gen.json via openapi-typescript
to generate src/api/types.ts — one source of truth for the API contract.

When all routes migrate to FastAPI in Phase 3-4, this script will be
replaced by FastAPI's built-in /openapi.json endpoint and this file
can be deleted.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow running this script from the repo root or from flask_voter_app/
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from app.schemas import (  # noqa: E402  (sys.path tweak above)
    AbstentionRequest,
    AbstentionResponse,
    CampaignSensitivityRequest,
    CampaignSensitivityResponse,
    CoalitionRequest,
    CoalitionResponse,
    CombinedEffectsRequest,
    CombinedEffectsResponse,
    SimulateRequest,
    SimulateResponse,
)


# Pairs (path, request_model, response_model, summary, operationId).
ENDPOINTS = [
    ("/api/election/simulate",
     SimulateRequest, SimulateResponse,
     "Run the unified election simulation",
     "simulateElection"),
    ("/api/election/combined-effects",
     CombinedEffectsRequest, CombinedEffectsResponse,
     "2x2x2 factorial: how each model (blank/campaign/info) shifts the result",
     "combinedEffects"),
    ("/api/election/campaign-sensitivity",
     CampaignSensitivityRequest, CampaignSensitivityResponse,
     "Snapshot the election at multiple campaign days",
     "campaignSensitivity"),
    ("/api/election/abstention",
     AbstentionRequest, AbstentionResponse,
     "Iterated abstention model with poll feedback",
     "abstention"),
    ("/api/election/coalition",
     CoalitionRequest, CoalitionResponse,
     "D'Hondt seat allocation + greedy coalition formation",
     "coalition"),
]


def _build_schema_refs() -> dict:
    """Collect every referenced model in a single components.schemas block."""
    components: dict[str, dict] = {}
    seen: set[str] = set()

    def add(model):
        if model.__name__ in seen:
            return
        seen.add(model.__name__)
        schema = model.model_json_schema(
            ref_template="#/components/schemas/{model}",
        )
        # Pydantic 2 sometimes nests its own definitions — flatten them up.
        for sub_name, sub_def in (schema.pop("$defs", {}) or {}).items():
            components[sub_name] = sub_def
        components[model.__name__] = schema

    for _, req, resp, _, _ in ENDPOINTS:
        add(req)
        add(resp)

    return components


def build_spec() -> dict:
    spec: dict = {
        "openapi": "3.1.0",
        "info": {
            "title":       "Vote Lab — Election API (Phase 1 typed subset)",
            "version":     "1.0.0",
            "description": (
                "Pydantic-derived contract for the 5 election endpoints typed in "
                "Phase 1 of the strategic refactor. The remaining endpoints will "
                "be added as they migrate to FastAPI in Phase 3."
            ),
        },
        "servers": [{"url": "http://localhost:4433"}],
        "paths":      {},
        "components": {"schemas": _build_schema_refs()},
    }

    for path, req, resp, summary, op_id in ENDPOINTS:
        spec["paths"][path] = {
            "post": {
                "operationId": op_id,
                "summary":     summary,
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": f"#/components/schemas/{req.__name__}"},
                        },
                    },
                },
                "responses": {
                    "200": {
                        "description": "OK",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": f"#/components/schemas/{resp.__name__}"},
                            },
                        },
                    },
                    "400": {"description": "Validation error"},
                    "429": {"description": "Rate limited"},
                    "500": {"description": "Internal error"},
                },
            },
        }

    return spec


def main() -> int:
    spec = build_spec()
    out_path = ROOT / "openapi.gen.json"
    out_path.write_text(json.dumps(spec, indent=2, sort_keys=False))
    n_paths   = len(spec["paths"])
    n_schemas = len(spec["components"]["schemas"])
    print(f"Wrote {out_path} ({n_paths} paths, {n_schemas} schemas).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
