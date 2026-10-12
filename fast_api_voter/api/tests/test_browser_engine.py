"""The engine in a browser (api/browser.py, EXP-023): the same answers as the server.

`browser.handle` answers a request through the server's own compute routers, in-process.
Every one of its POST routes is asked the body the server accepts and must return the
same status and the same JSON; so must an invalid body, a worker's own refusal and a GET
with a query string. Where threads do not exist (Pyodide), the workers run inline and the
Monte Carlo runs sequentially.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import threading
import zipfile
from pathlib import Path
from typing import Any

import pytest
from fastapi.routing import APIRoute, RouteContext, iter_route_contexts

from api import browser
from api.core import worker_dispatch
from api.core.ratelimit import check_v2_rate_limit
from api.domain.simulations import advanced
from api.engine.utils import runtime
from api.main import fastapi_app
from api.tests.test_no_global_rng import BODIES, CANDS, FALLBACKS

#: Unseeded by design (its docstring): only the status and the shape can match.
UNSEEDED = {"/api/v2/simulations/monte-carlo"}


def _ask(method: str, path: str, query: str = "", body: Any = None) -> tuple[int, Any]:
    status, text = asyncio.run(browser.handle(method, path, query, "" if body is None else json.dumps(body)))
    return status, json.loads(text)


def _contexts(app: Any) -> list[RouteContext]:
    """Every API route as served, with its full path and dependencies (FastAPI keeps an
    included router whole, so `app.routes` lists routers, not routes)."""
    return [c for c in iter_route_contexts(app.routes) if isinstance(c.route, APIRoute)]


def _routes(app: Any, method: str) -> list[str]:
    return sorted(c.path for c in _contexts(app) if method in c.methods)


@pytest.mark.parametrize("path", _routes(browser.app, "POST"))
def test_every_post_route_answers_as_the_server_does(client, path):
    for body in [BODIES[path]] if path in BODIES else FALLBACKS:
        served = client.post(path, json=body)
        if served.status_code == 200:
            break
    status, answer = _ask("POST", path, body=body)
    assert status == served.status_code
    if path in UNSEEDED:
        assert answer.keys() == served.json().keys()
    else:
        assert answer == served.json()


@pytest.mark.parametrize(
    ("path", "body"),
    [
        # Pydantic's own refusal: a 422 with the same detail.
        ("/api/v2/election/stv", {"candidates": "nobody"}),
        # The worker's refusal: as many seats as candidates is a 400.
        ("/api/v2/election/stv", {"candidates": CANDS[:3], "num_seats": 3, "num_voters": 60}),
        ("/api/v2/election/no-such-route", {}),
    ],
)
def test_refusals_match_the_server(client, path, body):
    served = client.post(path, json=body)
    assert _ask("POST", path, body=body) == (served.status_code, served.json())


def test_a_get_with_a_query_string_matches_the_server(client):
    query = "num_candidates=3&num_voters=50&num_trials=5&methods=plurality"
    served = client.get(f"/api/v2/simulations/manipulability?{query}")
    status, answer = _ask("GET", "/api/v2/simulations/manipulability", query)
    assert status == served.status_code == 200
    assert answer.keys() == served.json().keys()


#: Monitoring, never rate-limited: the liveness probe and Prometheus's scrape endpoint.
MONITORING = {"api.routes.health", "prometheus_fastapi_instrumentator.instrumentation"}
#: Server routes the browser does not serve, by the module of their endpoint: monitoring,
#: and Polity's run explorer, which reads run files from the server's disk.
SERVER_ONLY = MONITORING | {"api.routes.polity"}


def _v2(app: Any) -> list[RouteContext]:
    return [c for c in _contexts(app) if c.path.startswith("/api/v2/")]


def test_the_browser_app_serves_every_server_route_but_the_server_only_ones():
    """A route added to a router is in both apps; a new router must go into
    browser.ROUTERS or, deliberately, into SERVER_ONLY."""
    served = {(c.path, *sorted(c.methods)) for c in _v2(fastapi_app) if c.endpoint.__module__ not in SERVER_ONLY}
    assert served == {(c.path, *sorted(c.methods)) for c in _contexts(browser.app)}


def test_every_server_v2_route_but_monitoring_is_rate_limited():
    """The routers no longer carry the limiter: api/main.py adds it when it includes them.
    This checks the effective app, whatever a new router's prefix."""
    routes = [c for c in _v2(fastapi_app) if c.endpoint.__module__ not in MONITORING]
    assert routes
    unlimited = [c.path for c in routes if check_v2_rate_limit not in [d.call for d in c.dependant.dependencies]]
    assert unlimited == []


def test_without_threads_a_worker_runs_inline(monkeypatch):
    monkeypatch.setattr(runtime, "THREADS", False)
    here = threading.get_ident()
    assert asyncio.run(worker_dispatch.run_bounded(threading.get_ident)) == here


def test_without_threads_the_monte_carlo_runs_sequentially(monkeypatch):
    def no_threads(*_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError("can't start new thread")  # what Pyodide answers

    monkeypatch.setattr(runtime, "THREADS", False)
    monkeypatch.setattr(advanced, "ThreadPoolExecutor", no_threads)
    body, status = advanced._monte_carlo_worker({"candidates": CANDS, "num_voters": 50, "num_runs": 3})
    assert status == 200, body


def _builder() -> Any:
    script = Path(__file__).resolve().parents[2] / "scripts" / "build_browser_engine.py"
    spec = importlib.util.spec_from_file_location("build_browser_engine", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_bundle_ships_what_the_browser_imports_and_nothing_server_only(tmp_path):
    names = set(_builder().build(tmp_path / "engine.zip"))
    assert {"api/browser.py", "fastapi/__init__.py", "starlette/__init__.py", "typing_extensions.py"} <= names
    # A worker that imports inside its function is shipped too.
    assert "api/engine/utils/gibbard_satterthwaite.py" in names
    assert not {n for n in names if n in {"api/main.py"} or n.startswith(("api/tests/", "api/sockets/", "api/domain/polity/"))}
    with zipfile.ZipFile(tmp_path / "engine.zip") as z:
        assert z.testzip() is None


def test_the_bundle_refuses_a_package_the_browser_cannot_load(tmp_path, monkeypatch):
    builder = _builder()
    monkeypatch.setattr(builder, "BUNDLED", builder.BUNDLED - {"starlette"})
    with pytest.raises(SystemExit, match="starlette"):
        builder.build(tmp_path / "engine.zip")


def test_an_unhandled_error_is_the_servers_500(monkeypatch):
    """A route that raises: the catch-all handler's 500 JSON, as on the server, and the
    exception Starlette re-raises afterwards is logged, not lost."""
    @browser.app.get("/api/v2/raising-for-a-test")
    def _boom() -> None:
        raise ValueError("intentional")

    logged: list[str] = []
    monkeypatch.setattr(browser.log, "warning", lambda event, **_kw: logged.append(event))
    try:
        assert _ask("GET", "/api/v2/raising-for-a-test") == (500, {"detail": "Internal server error"})
        assert logged == ["browser.request_failed"]
    finally:
        browser.app.router.routes = [r for r in browser.app.router.routes if getattr(r, "path", None) != "/api/v2/raising-for-a-test"]
