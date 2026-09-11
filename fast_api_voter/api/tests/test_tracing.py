"""api/tests/test_tracing.py — Lot 10.2, PLAN_SOLIDITE_TECHNIQUE.md
("Observabilité"): asserts the per-voting-method OpenTelemetry span
(api/domain/simulations/base.py's `_traced_winner`, wrapping
`_simulate_votes_worker`'s ranked/scores branches) is actually created when
that code path runs — using the OpenTelemetry SDK's own in-memory span
exporter, so this stays a real, always-on regression test with no collector
needed. A real capture against a live Jaeger is verified manually and
documented in docs/exploration/EXP-014 — this file is the "doesn't silently
regress" half, not a substitute for that live check.

Module-scoped TracerProvider: `trace.set_tracer_provider()` is a one-shot
global in opentelemetry-api (a second call is a silent no-op with a logged
warning), so it's installed once here for the lifetime of this test
process/xdist worker rather than per-test. Harmless for every other test
module: production's own `configure_tracing()` (api/core/tracing.py) stays a
no-op in the test environment (OTEL_EXPORTER_OTLP_ENDPOINT is unset), so this
is the only place in the whole suite a real TracerProvider is ever installed
— any spans from unrelated tests that happen to share this worker process are
just extra entries `_clear_spans` discards before each assertion here.
"""
from __future__ import annotations

from typing import Any, Dict

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from api.domain.simulations.base import _simulate_votes_worker

_exporter = InMemorySpanExporter()
_provider = TracerProvider()
_provider.add_span_processor(SimpleSpanProcessor(_exporter))
trace.set_tracer_provider(_provider)


# Mirrors api/tests/test_simulations_base.py's _LEGACY_DEMOGRAPHICS.
_DEMOGRAPHICS: Dict[str, Any] = {
    "age": {"young": 0.3, "middle": 0.4, "old": 0.3},
    "gender": {"male": 0.5, "female": 0.5},
    "location": {"urban": 0.5, "suburban": 0.3, "rural": 0.2},
    "education": {"high_school": 0.3, "bachelor": 0.4, "master": 0.3},
    "income": {"low": 0.3, "middle": 0.4, "high": 0.3},
    "ideology": {"left": 0.3, "center": 0.4, "right": 0.3},
}


def _legacy_payload(simulation_type: str) -> Dict[str, Any]:
    return {
        "formData": {
            "simulationType": simulation_type,
            "populationSize": 10,
            "candidates": ["Alice", "Bob", "Carol"],
            "demographics": _DEMOGRAPHICS,
            "turnoutRate": 0.8,
            "influenceWeights": {"family": 0.3, "peers": 0.5, "media": 0.2},
        },
    }


@pytest.fixture(autouse=True)
def _clear_spans() -> Any:
    _exporter.clear()
    yield
    _exporter.clear()


class TestVotingMethodSpans:
    def test_ranked_branch_emits_a_span_per_method(self) -> None:
        body, status = _simulate_votes_worker(_legacy_payload("ranked"))
        assert status == 200, body

        spans = _exporter.get_finished_spans()
        names = {s.name for s in spans}
        methods = {s.attributes.get("voting.method") for s in spans if s.attributes}

        assert "voting_method.irv" in names
        assert "irv" in methods
        # The "ranked" branch computes exactly these 12 winners today (see
        # _simulate_votes_worker) — one span each.
        assert len(spans) == 12

    def test_scores_branch_emits_a_span_per_method(self) -> None:
        body, status = _simulate_votes_worker(_legacy_payload("scores"))
        assert status == 200, body

        spans = _exporter.get_finished_spans()
        names = {s.name for s in spans}
        methods = {s.attributes.get("voting.method") for s in spans if s.attributes}

        assert "voting_method.simple_score" in names
        assert "simple_score" in methods
        # The "scores" branch computes exactly these 6 winners today.
        assert len(spans) == 6

    def test_votes_branch_emits_no_voting_method_span(self) -> None:
        # The "votes" branch never calls a winner function (see
        # _simulate_votes_worker) — nothing to trace.
        body, status = _simulate_votes_worker(_legacy_payload("votes"))
        assert status == 200, body
        assert _exporter.get_finished_spans() == ()
