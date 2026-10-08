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
# The same private id generator as configure_tracing(): this provider stays
# installed for the whole session, and FastAPI 0.142+ opens a span on every
# request, so the SDK's default generator would make every later request draw
# from the global `random` (test_no_global_rng.py failed on #846 that way).
_provider = TracerProvider(id_generator=tracing.PrivateRandomIdGenerator())
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


def test_span_ids_leave_the_process_wide_random_alone():
    """Ids from the private generator never move the `random` singleton."""
    import random

    before = random.getstate()
    generator = tracing.PrivateRandomIdGenerator()
    ids = {generator.generate_span_id() for _ in range(50)} | {generator.generate_trace_id() for _ in range(50)}
    assert random.getstate() == before
    assert len(ids) == 100 and trace.INVALID_SPAN_ID not in ids
    assert generator.is_trace_id_random()


def test_an_invalid_id_is_drawn_again():
    """Zero is the invalid span/trace id: the generator draws again."""
    draws = iter([0, 7, 0, 9])

    class Scripted:
        def getrandbits(self, _bits):
            return next(draws)

    generator = tracing.PrivateRandomIdGenerator(rng=Scripted())
    assert generator.generate_span_id() == 7
    assert generator.generate_trace_id() == 9


def test_configure_tracing_installs_the_private_id_generator(monkeypatch):
    """The production provider gets the private generator, not the SDK default."""
    installed = []
    monkeypatch.setattr(tracing.trace, "set_tracer_provider", installed.append)
    monkeypatch.setattr(tracing, "get_settings",
                        lambda: Settings(otel_exporter_otlp_endpoint="http://localhost:4318"))
    tracing.configure_tracing()
    assert isinstance(installed[0].id_generator, tracing.PrivateRandomIdGenerator)
