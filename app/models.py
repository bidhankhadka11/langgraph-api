"""
API Request and Response Models
Pydantic models for input validation and response structure
"""

from pydantic import BaseModel, Field
from datetime import datetime, timezone


class ChatRequest(BaseModel):
    """Incoming Chat Request"""

    message: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="The user's message to the agent",
    )
    thread_id: str = Field(default="default", description="Conversation thread ID")


class ChatResponse(BaseModel):
    """Chat Response returned to the client"""

    response: str
    thread_id: str
    model_used: str
    cached: bool = False
    processing_time_ms: float
    security_notes: list[str] = Field(default_factory=list)
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class HealthResponse(BaseModel):
    """Health Check Response"""

    status: str = "healthy"
    environment: str
    version: str = "1.0.0"
    checks: dict = {}


class MetricsResponse(BaseModel):
    """Metrics endpoint response."""

    total_requests: int
    total_errors: int
    error_rate: str
    avg_latency_ms: float
    cache_hit_rate: str
    total_input_tokens: int
    total_output_tokens: int


class ErrorResponse(BaseModel):
    """Standard Error Response"""

    error: str
    detail: str | None = None
    request_id: str | None = None
