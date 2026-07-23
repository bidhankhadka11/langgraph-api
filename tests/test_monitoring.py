"""
Tests for structured logging and metrics (app/monitoring.py).
Fast, deterministic, no external dependencies.
"""
import json
import logging
import time

from app.monitoring import JSONFormatter, MetricsCollector, RequestTimer, get_logger


class TestMetricsCollector:
    def setup_method(self):
        self.m = MetricsCollector()

    def test_records_counts_latency_and_tokens(self):
        self.m.record_request(100.0, input_tokens=10, output_tokens=20)  # miss
        self.m.record_request(0.0, cached=True)                          # hit
        self.m.record_request(50.0, error=True)                          # miss + error

        snap = self.m.snapshot()
        assert snap["total_requests"] == 3
        assert snap["total_errors"] == 1
        assert snap["error_rate"] == "33.3%"
        assert snap["avg_latency_ms"] == 50.0        # (100 + 0 + 50) / 3
        assert snap["cache_hit_rate"] == "33.3%"     # 1 hit / (1 hit + 2 miss)
        assert snap["total_input_tokens"] == 10
        assert snap["total_output_tokens"] == 20

    def test_empty_snapshot_has_safe_zeros(self):
        snap = self.m.snapshot()
        assert snap["total_requests"] == 0
        assert snap["error_rate"] == "0.0%"
        assert snap["avg_latency_ms"] == 0.0
        assert snap["cache_hit_rate"] == "0.0%"

    def test_reset_zeros_everything(self):
        self.m.record_request(100.0, input_tokens=5, output_tokens=5, cached=True)
        self.m.reset()
        snap = self.m.snapshot()
        assert snap["total_requests"] == 0
        assert snap["total_input_tokens"] == 0
        assert snap["total_output_tokens"] == 0


class TestRequestTimer:
    def test_measures_positive_duration(self):
        with RequestTimer() as timer:
            time.sleep(0.01)
        ms = timer.elapsed_ms
        assert isinstance(ms, float)
        assert ms > 0
        # frozen after exit — repeated reads are stable
        assert timer.elapsed_ms == ms

    def test_unstarted_timer_is_zero(self):
        assert RequestTimer().elapsed_ms == 0.0


class TestJSONFormatter:
    def test_produces_valid_json_with_expected_fields(self):
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname=__file__, lineno=10,
            msg="hello %s", args=("world",), exc_info=None,
        )
        data = json.loads(JSONFormatter().format(record))
        assert data["level"] == "INFO"
        assert data["message"] == "hello world"
        assert "timestamp" in data
        assert "module" in data
        assert "function" in data

    def test_extra_fields_are_merged(self):
        record = logging.LogRecord(
            name="test", level=logging.WARNING, pathname=__file__, lineno=11,
            msg="warn", args=(), exc_info=None,
        )
        record.extra_fields = {"request_id": "abc123"}
        data = json.loads(JSONFormatter().format(record))
        assert data["request_id"] == "abc123"
        assert data["level"] == "WARNING"


class TestGetLogger:
    def test_returns_logger_with_single_json_handler(self):
        logger = get_logger("test-logger-unique")
        assert isinstance(logger, logging.Logger)
        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0].formatter, JSONFormatter)
        # idempotent: calling again does not stack more handlers
        again = get_logger("test-logger-unique")
        assert again is logger
        assert len(again.handlers) == 1
