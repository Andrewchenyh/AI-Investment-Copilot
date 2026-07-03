from observability.metrics import MetricsCollector, percentile


def test_percentile_empty_values() -> None:
    assert percentile([], 50) is None


def test_percentile_single_value() -> None:
    assert percentile([10.0], 95) == 10.0


def test_metrics_snapshot() -> None:
    collector = MetricsCollector()

    collector.record_request_latency(100)
    collector.record_request_latency(300)

    collector.record_tool_execution(
        latency_ms=50,
        success=True,
        cache_hit=False,
    )
    collector.record_tool_execution(
        latency_ms=10,
        success=True,
        cache_hit=True,
    )
    collector.record_tool_execution(
        latency_ms=20,
        success=False,
        cache_hit=False,
    )

    snapshot = collector.snapshot()

    assert snapshot["requests"]["count"] == 2
    assert snapshot["requests"]["p50_latency_ms"] == 100
    assert snapshot["requests"]["p95_latency_ms"] == 300

    assert snapshot["tools"]["count"] == 3
    assert snapshot["tools"]["success_count"] == 2
    assert snapshot["tools"]["failure_count"] == 1
    assert snapshot["tools"]["failure_rate"] == 1 / 3
    assert snapshot["tools"]["cache_hit_count"] == 1
    assert snapshot["tools"]["cache_miss_count"] == 2
    assert snapshot["tools"]["cache_hit_rate"] == 1 / 3