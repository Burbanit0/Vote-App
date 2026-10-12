"""The answers the engine in the browser must give (W6, EXP-023), as CPython gives them.

Writes, as JSON, what api/tests/test_browser_engine.py asks the engine and the server, with
the answer `api.browser.handle` gives here: every POST route the in-browser app serves (the
first body it accepts), the GET with a query string and the refusals. That test holds these
answers to the server's; voter-app/tests/e2e/static.spec.ts holds the static build's
engine.zip, under Pyodide, to these: the same status and JSON, or, for an unseeded route
("exact": false), the same status and keys.

Usage, from fast_api_voter/: python scripts/browser_engine_answers.py <out.json>
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.routing import APIRoute, iter_route_contexts  # noqa: E402

from api import browser  # noqa: E402
from api.tests.route_bodies import BODIES, FALLBACKS, GET, REFUSALS, UNSEEDED  # noqa: E402


def _ask(method: str, path: str, query: str, body: Any) -> dict[str, Any]:
    status, text = asyncio.run(browser.handle(method, path, query, "" if body is None else json.dumps(body)))
    return {"method": method, "path": path, "query": query, "body": body, "status": status,
            "answer": json.loads(text), "exact": path not in UNSEEDED}


def _post(path: str) -> dict[str, Any]:
    """The route's answer to the first body it accepts (the last tried, if none)."""
    for body in [BODIES[path]] if path in BODIES else FALLBACKS:
        asked = _ask("POST", path, "", body)
        if asked["status"] == 200:
            break
    return asked


def answers() -> list[dict[str, Any]]:
    posts = sorted(str(c.path) for c in iter_route_contexts(browser.app.routes)
                   if isinstance(c.route, APIRoute) and "POST" in (c.methods or ()))
    return ([_post(path) for path in posts] + [_ask("GET", *GET, None)]
            + [_ask("POST", path, "", body) for path, body in REFUSALS])


if __name__ == "__main__":
    Path(sys.argv[1]).write_text(json.dumps(answers()))
