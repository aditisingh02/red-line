"""Observability facade — Prometheus metrics + OpenTelemetry traces.

Both backends are optional. If `prometheus_client` / `opentelemetry` are not
installed (or OTEL has no endpoint configured) every call here becomes a
cheap no-op, mirroring the "live sources degrade gracefully" contract used
elsewhere in the scanner. Nothing in this module is ever allowed to raise.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager

from .config import settings

log = logging.getLogger("redline.observability")

# --- Prometheus -------------------------------------------------------------
try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        CollectorRegistry,
        Counter,
        Histogram,
        generate_latest,
    )

    _PROM = True
except Exception:  # noqa: BLE001 — optional dependency
    _PROM = False


class _NoopMetric:
    """Stand-in with the prometheus_client surface we use."""

    def labels(self, *_a, **_kw) -> "_NoopMetric":
        return self

    def inc(self, *_a, **_kw) -> None:
        pass

    def observe(self, *_a, **_kw) -> None:
        pass


if _PROM:
    _REGISTRY = CollectorRegistry()
    SCANS_STARTED = Counter(
        "redline_scans_started_total", "Scans started", registry=_REGISTRY)
    SCANS_COMPLETED = Counter(
        "redline_scans_completed_total", "Scans completed", ["status"],
        registry=_REGISTRY)
    FINDINGS = Counter(
        "redline_findings_total", "Findings by severity", ["severity"],
        registry=_REGISTRY)
    TEST_DURATION = Histogram(
        "redline_test_duration_seconds", "Per-payload execution time",
        buckets=(0.1, 0.25, 0.5, 1, 2, 5, 10), registry=_REGISTRY)
    SCORER_CALLS = Counter(
        "redline_scorer_calls_total", "Scorer invocations", ["backend"],
        registry=_REGISTRY)
else:  # pragma: no cover - exercised only without prometheus_client
    SCANS_STARTED = SCANS_COMPLETED = FINDINGS = _NoopMetric()
    TEST_DURATION = SCORER_CALLS = _NoopMetric()


def metrics_enabled() -> bool:
    return _PROM and settings.redline_metrics_enabled


def render_metrics() -> tuple[bytes, str]:
    """Body + content-type for the /metrics endpoint."""
    if not metrics_enabled():
        note = (b"# metrics disabled or prometheus_client not installed\n")
        return note, "text/plain; version=0.0.4; charset=utf-8"
    return generate_latest(_REGISTRY), CONTENT_TYPE_LATEST


# --- OpenTelemetry ----------------------------------------------------------
_tracer = None
try:
    if settings.otel_exporter_otlp_endpoint:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        _provider = TracerProvider(
            resource=Resource.create({"service.name": "redline"}))
        _provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(
            endpoint=settings.otel_exporter_otlp_endpoint)))
        trace.set_tracer_provider(_provider)
        _tracer = trace.get_tracer("redline")
        log.info("OpenTelemetry tracing -> %s",
                 settings.otel_exporter_otlp_endpoint)
except Exception as e:  # noqa: BLE001 — tracing is best-effort
    log.warning("OpenTelemetry disabled: %s", e)
    _tracer = None


@contextmanager
def span(name: str, **attributes):
    """Trace a block if OTEL is configured; otherwise a zero-cost no-op."""
    if _tracer is None:
        yield None
        return
    with _tracer.start_as_current_span(name) as sp:  # pragma: no cover
        try:
            for k, v in attributes.items():
                sp.set_attribute(k, v)
        except Exception:  # noqa: BLE001
            pass
        yield sp


def tracing_enabled() -> bool:
    return _tracer is not None
