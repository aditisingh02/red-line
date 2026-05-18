from redline import observability as obs


def test_metrics_render_returns_body_and_content_type():
    body, ctype = obs.render_metrics()
    assert isinstance(body, bytes)
    assert "text" in ctype or "plain" in ctype


def test_metric_calls_never_raise():
    # Works whether prometheus_client is installed or not.
    obs.SCANS_STARTED.inc()
    obs.SCANS_COMPLETED.labels(status="completed").inc()
    obs.FINDINGS.labels(severity="critical").inc()
    obs.TEST_DURATION.observe(0.5)
    obs.SCORER_CALLS.labels(backend="regex").inc()


def test_span_is_safe_noop_when_tracing_disabled():
    # No OTEL endpoint configured in tests -> tracing disabled.
    assert obs.tracing_enabled() is False
    with obs.span("unit.test", target="x") as sp:
        assert sp is None
