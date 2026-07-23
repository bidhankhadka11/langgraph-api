"""
Tests for the Pydantic request/response contracts (app/models.py).
"""
import pytest
from pydantic import ValidationError

from app.models import (
    ChatRequest, ChatResponse, HealthResponse, MetricsResponse, ErrorResponse,
)


class TestChatRequest:
    def test_valid_request_defaults_thread_id(self):
        req = ChatRequest(message="Hello")
        assert req.message == "Hello"
        assert req.thread_id == "default"

    def test_missing_message_rejected(self):
        with pytest.raises(ValidationError):
            ChatRequest(thread_id="x")

    def test_empty_message_rejected(self):
        with pytest.raises(ValidationError):
            ChatRequest(message="")

    def test_overlong_message_rejected(self):
        with pytest.raises(ValidationError):
            ChatRequest(message="a" * 1001)


class TestChatResponse:
    def test_valid_response(self):
        resp = ChatResponse(
            response="Hi", thread_id="t1", model_used="primary",
            processing_time_ms=12.5,
        )
        assert resp.cached is False
        assert resp.security_notes == []
        assert isinstance(resp.timestamp, str)

    def test_missing_required_field_rejected(self):
        with pytest.raises(ValidationError):
            ChatResponse(response="Hi", thread_id="t1", model_used="primary")

    def test_non_numeric_processing_time_rejected(self):
        with pytest.raises(ValidationError):
            ChatResponse(
                response="Hi", thread_id="t1", model_used="primary",
                processing_time_ms="not-a-number",
            )


class TestOtherModels:
    def test_health_response_defaults(self):
        h = HealthResponse(environment="development")
        assert h.status == "healthy"
        assert h.version == "1.0.0"

    def test_metrics_response_requires_all_fields(self):
        with pytest.raises(ValidationError):
            MetricsResponse(total_requests=1)  # missing the rest

    def test_metrics_response_valid(self):
        m = MetricsResponse(
            total_requests=3, total_errors=0, error_rate="0.0%",
            avg_latency_ms=1.2, cache_hit_rate="50.0%",
            total_input_tokens=10, total_output_tokens=20,
        )
        assert m.total_requests == 3

    def test_error_response_detail_optional(self):
        e = ErrorResponse(error="boom")
        assert e.detail is None
