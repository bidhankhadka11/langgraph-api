"""
Monitoring & Structured Logging
Production-grade metrics collection and JSON logging
"""

import logging
import json
import time
import threading
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable

class JSONFormatter(logging.Formatter):
    """Format log records as JSON for log aggregation (ELK, Datadog, etc)"""

    def format(self, record):
        log_obj = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
        }

        if hasattr(record, "extra_fields"):
            log_obj.update(record.extra_fields)
        return json.dumps(log_obj)

def get_logger(name:str = "production-api") -> logging.Logger:
    """Create a structured JSON logger"""
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    return logger


class MetricsCollector:
    """
    In-memory metrics collector for the API.

    Tracks request volume, errors, latency, cache efficiency, and token
    usage. Its snapshot() output maps directly onto MetricsResponse
    (see app/models.py) and feeds the /metrics endpoint.

    Thread-safe: FastAPI serves requests concurrently, so all counter
    updates are guarded by a lock.

    In production, export these to Prometheus / Datadog instead of holding
    them in process memory (this resets on restart and is per-instance only).
    """

    def __init__(self):
        self._lock = threading.Lock()
        self.total_requests = 0
        self.total_errors = 0
        self.total_latency_ms = 0.0
        self.cache_hits = 0
        self.cache_misses = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    def record_request(
        self,
        latency_ms: float,
        *,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cached: bool = False,
        error: bool = False,
    ) -> None:
        """Record a single handled request. Call once per request."""
        with self._lock:
            self.total_requests += 1
            self.total_latency_ms += latency_ms
            if error:
                self.total_errors += 1
            if cached:
                self.cache_hits += 1
            else:
                self.cache_misses += 1
            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens

    def snapshot(self) -> dict[str, Any]:
        """Return a point-in-time metrics summary (shape matches MetricsResponse)."""
        with self._lock:
            total = self.total_requests
            cache_total = self.cache_hits + self.cache_misses
            error_rate = (self.total_errors / total) if total else 0.0
            avg_latency = (self.total_latency_ms / total) if total else 0.0
            cache_hit_rate = (self.cache_hits / cache_total) if cache_total else 0.0

            return {
                "total_requests": total,
                "total_errors": self.total_errors,
                "error_rate": f"{error_rate:.1%}",
                "avg_latency_ms": round(avg_latency, 2),
                "cache_hit_rate": f"{cache_hit_rate:.1%}",
                "total_input_tokens": self.total_input_tokens,
                "total_output_tokens": self.total_output_tokens,
            }

    def reset(self) -> None:
        """Reset all counters to zero (useful for tests)."""
        with self._lock:
            self.total_requests = 0
            self.total_errors = 0
            self.total_latency_ms = 0.0
            self.cache_hits = 0
            self.cache_misses = 0
            self.total_input_tokens = 0
            self.total_output_tokens = 0


class RequestTimer:
    """
    Context manager for measuring elapsed wall-clock time of a request.

    Usage:
        with RequestTimer() as timer:
            ...do work...
        print(timer.elapsed_ms)

    elapsed_ms is readable both inside the block (time so far) and after
    it exits (final duration).
    """

    def __init__(self):
        self._start = None
        self._end = None

    def __enter__(self) -> "RequestTimer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._end = time.perf_counter()

    @property
    def elapsed_ms(self) -> float:
        """Elapsed milliseconds. Uses the frozen end time once the block exits."""
        if self._start is None:
            return 0.0
        end = self._end if self._end is not None else time.perf_counter()
        return (end - self._start) * 1000


# Shared singleton — import this into routes to record/read metrics.
metrics = MetricsCollector()