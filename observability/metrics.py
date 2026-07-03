from __future__ import annotations

from threading import Lock


class MetricsCollector:
    def __init__(self) -> None:
        self._lock = Lock()
        self.request_latencies_ms: list[float] = []
        self.tool_latencies_ms: list[float] = []
        self.tool_success_count = 0
        self.tool_failure_count = 0
        self.cache_hit_count = 0
        self.cache_miss_count = 0

    def record_request_latency(self, latency_ms: float) -> None:
        with self._lock:
            self.request_latencies_ms.append(latency_ms)

    def record_tool_execution(
        self,
        latency_ms: float,
        success: bool,
        cache_hit: bool,
    ) -> None:
        with self._lock:
            self.tool_latencies_ms.append(latency_ms)

            if success:
                self.tool_success_count += 1
            else:
                self.tool_failure_count += 1

            if cache_hit:
                self.cache_hit_count += 1
            else:
                self.cache_miss_count += 1

    def snapshot(self) -> dict:
        with self._lock:
            request_latencies = list(self.request_latencies_ms)
            tool_success_count = self.tool_success_count
            tool_failure_count = self.tool_failure_count
            cache_hit_count = self.cache_hit_count
            cache_miss_count = self.cache_miss_count

        total_tools = tool_success_count + tool_failure_count
        total_cache = cache_hit_count + cache_miss_count

        return {
            "requests": {
                "count": len(request_latencies),
                "p50_latency_ms": percentile(request_latencies, 50),
                "p95_latency_ms": percentile(request_latencies, 95),
            },
            "tools": {
                "count": total_tools,
                "failure_rate": (
                    tool_failure_count / total_tools if total_tools else 0
                ),
                "cache_hit_rate": (
                    cache_hit_count / total_cache if total_cache else 0
                ),
                "success_count": tool_success_count,
                "failure_count": tool_failure_count,
                "cache_hit_count": cache_hit_count,
                "cache_miss_count": cache_miss_count,
            },
        }


def percentile(values: list[float], p: int) -> float | None:
    if not values:
        return None

    sorted_values = sorted(values)
    index = int(round((p / 100) * (len(sorted_values) - 1)))
    return round(sorted_values[index], 2)


metrics = MetricsCollector()