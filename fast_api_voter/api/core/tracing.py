"""
api.core.tracing — OpenTelemetry tracing (Lot 10.2, PLAN_SOLIDITE_TECHNIQUE.md
— "Observabilité"). Traces per HTTP request (auto-instrumentation) plus an
explicit span per voting-method computation, so a trace shows real per-method
timing — not just per-request timing — feeding back into the perf numbers
Lot 8 already measured (api/tests/test_engine_benchmarks.py).

Same optional-dependency pattern as Redis (redis_url) and this file's other
settings: `OTEL_EXPORTER_OTLP_ENDPOINT` empty (the default) means tracing is
fully disabled — `configure_tracing()`/`instrument_app()` are no-ops, and
every `trace.get_tracer(__name__).start_as_current_span(...)` call anywhere
in the codebase (see api/domain/simulations/base.py) keeps resolving to
opentelemetry-api's own no-op tracer, which costs a few no-op attribute
calls and exports nothing. That degrade-to-no-op behaviour is the standard
OpenTelemetry pattern precisely so call sites never need an `if
tracing_enabled` conditional of their own.

Jaeger all-in-one, not a hosted APM SaaS: this repo just adopted self-hosted
GlitchTip for error tracking over any SaaS option (a separate, concurrent
piece of work) — this stays consistent with that already-stated preference
rather than introducing a fresh, unconfirmed one. See docs/exploration/
EXP-014 for the full reasoning, including a live-verified surprise: the
`jaegertracing/all-in-one` Docker Hub image is effectively frozen (last
pushed ~9 months before this was written) — Jaeger v2 replaced it with a
unified binary published as `jaegertracing/jaeger`, which is what
docker-compose.observability-tracing.yml actually runs.

OTLP/HTTP, not gRPC: confirmed live that Jaeger v2 all-in-one exposes both
OTLP receivers by default (4317 grpc, 4318 http) — either works. HTTP was
picked because `opentelemetry-exporter-otlp-proto-http` has no `grpcio`
dependency, and this repo already treats Python-3.14 wheel availability as a
real constraint worth avoiding where there's no functional reason not to
(requirements.txt's scipy comment tracks the same class of issue) — grpcio
does now ship a cp314 wheel (confirmed by download, not assumed), so this
is a "no reason to pay for it" choice, not a compatibility workaround.
"""
from __future__ import annotations

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from api.core.config import get_settings
from api.engine.utils.logger import get_logger

log = get_logger(__name__)


def configure_tracing() -> None:
    """Install a `TracerProvider` exporting to `OTEL_EXPORTER_OTLP_ENDPOINT`
    via OTLP/HTTP. No-op when that setting is empty (the default) — call
    unconditionally from api.main's startup path.

    Idempotency note: `trace.set_tracer_provider` is a process-global,
    one-time-effective call in opentelemetry-api (a second call logs a
    warning and is ignored) — safe under uvicorn's `--reload`, which
    re-imports api.main in the same process on a file change, and under
    running the test suite, which imports api.main once per session.
    """
    settings = get_settings()
    endpoint = settings.otel_exporter_otlp_endpoint
    if not endpoint:
        return

    provider = TracerProvider(
        resource=Resource.create({SERVICE_NAME: settings.otel_service_name})
    )
    # The HTTP exporter only auto-appends "/v1/traces" when it reads the
    # endpoint from the OTEL_EXPORTER_OTLP_ENDPOINT env var itself (verified
    # against the installed exporter's source) — an explicit `endpoint=` kwarg
    # is used as-is, so the path is appended here instead.
    exporter = OTLPSpanExporter(endpoint=f"{endpoint.rstrip('/')}/v1/traces")
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    log.info(
        "tracing.configured",
        endpoint=endpoint,
        service_name=settings.otel_service_name,
    )


def instrument_app(app: FastAPI) -> None:
    """Auto-instrument `app` for one span per HTTP request. No-op when
    tracing is disabled, so a request never pays for ASGI instrumentation
    that would export nowhere anyway."""
    if not get_settings().otel_exporter_otlp_endpoint:
        return
    FastAPIInstrumentor.instrument_app(app)
