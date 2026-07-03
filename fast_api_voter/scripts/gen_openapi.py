"""
scripts/gen_openapi.py — dump the FastAPI OpenAPI schema to openapi.gen.json.

Offline: imports the app and calls `.openapi()` — no running server needed.
The frontend turns this into TypeScript types via `npm run gen:api`
(openapi-typescript), so the Pydantic request/response contracts are the single
source of truth shared backend ↔ frontend.

Usage:
    cd fast_api_voter
    python scripts/gen_openapi.py            # -> fast_api_voter/openapi.gen.json
    cd ../voter-app && npm run gen:api       # -> src/api/types.gen.ts
"""
from __future__ import annotations

import json
import os
import sys

# Make `import api.*` work when run from fast_api_voter/ or scripts/.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# A secret must be set or the production-guard in main's lifespan is irrelevant
# (we never start the server here), but config import is cheap and side-effect free.
os.environ.setdefault("APP_ENV", "development")

from api.main import fastapi_app  # noqa: E402

OUTPUT = os.path.join(os.path.dirname(__file__), "..", "openapi.gen.json")


def main() -> None:
    spec = fastapi_app.openapi()
    with open(os.path.abspath(OUTPUT), "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    paths = len(spec.get("paths", {}))
    schemas = len(spec.get("components", {}).get("schemas", {}))
    print(f"Wrote {os.path.abspath(OUTPUT)} — {paths} paths, {schemas} schemas.")


if __name__ == "__main__":
    main()
