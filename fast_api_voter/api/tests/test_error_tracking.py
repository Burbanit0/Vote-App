"""Tests for Lot 10.1 (PLAN_SOLIDITE_TECHNIQUE.md) — self-hosted GlitchTip
error tracking.

Uses sentry_sdk's own `Transport` abstraction to swap in a fake, capturing
transport instead of a real one — the same pattern sentry-python's own test
suite uses internally (its conftest.py's `capture_events` fixture). Passing a
`Transport` instance as `sentry_sdk.init(transport=...)` is a supported path,
confirmed against the installed sentry-sdk 2.69.1 source
(`sentry_sdk.transport.make_transport`: `if isinstance(ref_transport,
Transport): transport = ref_transport`), not assumed from documentation. No
network call ever happens here and no real GlitchTip/Sentry instance is
required to run this file.
"""
from __future__ import annotations

from typing import Any

import pytest
import sentry_sdk
from fastapi.testclient import TestClient
from sentry_sdk.client import NonRecordingClient
from sentry_sdk.transport import Transport

from api.core.config import Settings
from api.main import _init_sentry, app, fastapi_app

_RAISING_PATH = "/api/v2/__test_only_raises_for_sentry_regression"


class _CapturingTransport(Transport):
    """Never sends anything over the network — just remembers every event
    captured in this process so the test can inspect it directly."""

    def __init__(self) -> None:
        super().__init__()
        self.events: list[dict[str, Any]] = []

    def capture_envelope(self, envelope: Any) -> None:
        for item in envelope:
            if item.headers.get("type") == "event":
                self.events.append(item.payload.json)


@pytest.fixture
def sentry_events():
    """Activate sentry_sdk for one test, capturing into a list instead of
    sending anywhere, then fully deactivate it again so later tests in the
    same process aren't affected."""
    transport = _CapturingTransport()
    # A syntactically valid DSN is required even though nothing is ever sent
    # over it (the fake transport intercepts everything) — sentry_sdk parses
    # it eagerly at init time.
    sentry_sdk.init(dsn="https://[email protected]/1", transport=transport)
    try:
        yield transport.events
    finally:
        sentry_sdk.get_global_scope().set_client(NonRecordingClient())


@pytest.fixture
def _raising_route():
    """Registers a route on the real app that always raises, so the test
    exercises the exact code path api/main.py's `_unhandled_exception_handler`
    guards in production. Removed again after the test so it never leaks into
    the running app or other tests."""

    @fastapi_app.get(_RAISING_PATH)
    def _boom() -> None:
        raise ValueError("Lot 10.1 regression test — this exception is intentional")

    yield _RAISING_PATH
    fastapi_app.router.routes = [
        r for r in fastapi_app.router.routes if getattr(r, "path", None) != _RAISING_PATH
    ]


class TestSentryInitGating:
    """Mirrors api/routes/health.py's _check_redis two-branch coverage: an
    optional dependency gated on a settings field must be tested disabled AND
    enabled, not just imported and trusted."""

    def test_disabled_when_dsn_is_unset(self, monkeypatch):
        calls = []
        monkeypatch.setattr(sentry_sdk, "init", lambda **kw: calls.append(kw))
        _init_sentry(Settings(glitchtip_dsn=""))
        assert calls == []

    def test_enabled_when_dsn_is_set(self, monkeypatch):
        calls = []
        monkeypatch.setattr(sentry_sdk, "init", lambda **kw: calls.append(kw))
        _init_sentry(Settings(glitchtip_dsn="https://public@glitchtip.example/7", app_env="production"))
        assert calls == [{"dsn": "https://public@glitchtip.example/7", "environment": "production"}]


class TestCatchAllHandlerReportsToSentry:
    def test_unhandled_exception_is_captured_as_a_sentry_event(self, sentry_events, _raising_route):
        """The load-bearing claim of Lot 10.1: configure_logging()
        (api/engine/utils/logger.py) routes every `log.error(...)` through
        stdlib logging, and sentry_sdk's default LoggingIntegration turns any
        stdlib `.error()`/`.exception()` call into a captured event — so the
        catch-all handler's own `_unhandled_log.error("http.unhandled_
        exception", ..., exc_info=True)` reaches GlitchTip with zero extra
        plumbing. Proven here, not assumed.

        NOTE: TestClient's default `raise_server_exceptions=True` re-raises
        the exception to the *caller* of client.get(...) even though the app
        already handled it and produced a real response — a Starlette
        BaseHTTPMiddleware quirk that surfaces here because this app stacks
        several `@app.middleware("http")` handlers on top of a registered
        `Exception` handler. `raise_server_exceptions=False` is required to
        see what a real client over HTTP actually receives; confirmed live
        against an actual `uvicorn` process too (see docs/exploration/
        EXP-012 for the full trace).
        """
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get(_raising_route)

        assert response.status_code == 500
        assert response.json() == {"detail": "Internal server error"}

        loggers = [e.get("logger") for e in sentry_events]
        assert "api.unhandled" in loggers, sentry_events

        captured = next(e for e in sentry_events if e.get("logger") == "api.unhandled")
        assert "http.unhandled_exception" in captured["logentry"]["message"]
