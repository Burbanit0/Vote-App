"""api/tests/test_tracing.py — Lot 10.2, PLAN_SOLIDITE_TECHNIQUE.md
("Observabilité"): covers the enabled branch of api/core/tracing.py —
configure_tracing() and instrument_app() when an OTLP endpoint IS configured.

Module-scoped TracerProvider: `trace.set_tracer_provider()` is a one-shot
global in opentelemetry-api (a second call is a silent no-op with a logged
warning), so an in-memory provider is installed once here. That keeps
configure_tracing()'s own `set_tracer_provider(...)` below a harmless no-op,
instead of wiring a real OTLP exporter into this test process.
"""
from __future__ import annotations

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from api.core import tracing
from api.core.config import Settings

_exporter = InMemorySpanExporter()
_provider = TracerProvider()
_provider.add_span_processor(SimpleSpanProcessor(_exporter))
trace.set_tracer_provider(_provider)


class TestConfigureTracingAndInstrumentApp:
    """The disabled path (empty OTEL_EXPORTER_OTLP_ENDPOINT) is already
    exercised implicitly by every other test in this suite -- api.main
    imports and calls configure_tracing()/instrument_app() at collection
    time, with tracing unset in the test environment. This class covers the
    other branch: what actually runs when an endpoint IS configured.

    Doesn't assert against a real collector (that's EXP-014's live-verified
    manual check) -- just that the enabled code path executes without
    raising, using a real (if unreachable) OTLP endpoint and exporter.

    `trace.set_tracer_provider` is a one-shot global (see this module's own
    docstring): this file's module-level import has already installed the
    in-memory provider, so configure_tracing()'s own
    `trace.set_tracer_provider(...)` call here is a harmless, already-a-
    no-op call -- it still executes every line, it just doesn't replace it.
    """

    def test_configure_tracing_builds_a_real_provider_and_exporter(self, monkeypatch):
        fake_settings = Settings(
            otel_exporter_otlp_endpoint="http://localhost:4318",
            otel_service_name="test-vote-lab-api",
        )
        monkeypatch.setattr(tracing, "get_settings", lambda: fake_settings)

        tracing.configure_tracing()  # must not raise

    def test_instrument_app_wraps_a_fresh_app_when_endpoint_is_set(self, monkeypatch):
        fake_settings = Settings(otel_exporter_otlp_endpoint="http://localhost:4318")
        monkeypatch.setattr(tracing, "get_settings", lambda: fake_settings)

        # A throwaway FastAPI instance, never the shared api.main app --
        # FastAPIInstrumentor patches the app it's given, and re-instrumenting
        # the real app here would double-wrap it for every other test in the
        # suite that imports api.main.
        tracing.instrument_app(FastAPI())  # must not raise
