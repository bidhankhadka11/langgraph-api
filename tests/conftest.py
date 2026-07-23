"""
Shared test fixtures.

Sets dummy API keys and disables LangSmith tracing BEFORE any app module is
imported, so config loads without real credentials and no test ever touches the
network. LLM clients are replaced with a deterministic FakeLLM.
"""

import os

# Must run before app.config / app.main import (they call get_settings() and
# load_dotenv() at import time). setdefault + tracing-off keeps tests offline.
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGSMITH_TRACING"] = "false"

import pytest
from langchain_core.messages import AIMessage


class FakeLLM:
    """Deterministic stand-in for ChatOpenAI / ChatAnthropic — no network.

    Configure with a fixed `response`, or an `exc` to raise on invoke().
    Tracks how many times invoke() was called.
    """

    def __init__(self, response="fake response", exc=None, **kwargs):
        self.response = response
        self.exc = exc
        self.calls = 0
        self.init_kwargs = kwargs

    def invoke(self, messages):
        self.calls += 1
        if self.exc is not None:
            raise self.exc
        return AIMessage(content=self.response)


class FakeAgent:
    """Stand-in for ProductionAgent at the API boundary. Records the messages
    it was invoked with so tests can assert cache short-circuiting and
    sanitization."""

    def __init__(self, response="Mocked answer.", model_used="primary", error=None):
        self.response = response
        self.model_used = model_used
        self.error = error
        self.calls = []

    def invoke(self, message):
        self.calls.append(message)
        return {
            "response": self.response,
            "model_used": self.model_used,
            "error": self.error,
        }


@pytest.fixture(autouse=True)
def patch_llms(monkeypatch):
    """Replace the real LLM client classes so ProductionAgent() never builds a
    real client or needs a live key. Autouse so it applies before any fixture
    that constructs an agent (directly or via the app lifespan)."""
    monkeypatch.setattr("app.agent.ChatOpenAI", FakeLLM)
    monkeypatch.setattr("app.agent.ChatAnthropic", FakeLLM)
    yield


@pytest.fixture
def agent(patch_llms):
    """A ProductionAgent whose graph is real but whose LLMs are FakeLLMs.
    Tests assign agent.primary_llm / agent.fallback_llm to control behavior."""
    from app.agent import ProductionAgent

    return ProductionAgent()


@pytest.fixture
def client():
    """FastAPI TestClient with the lifespan run (globals initialized), the
    rate limiter disabled, and the agent replaced by a FakeAgent.

    The FakeAgent is attached as `client.fake_agent`. Tests that need custom
    agent behavior reassign `app.main.agent` themselves.
    """
    from fastapi.testclient import TestClient
    import app.main as main

    with TestClient(main.app) as c:
        main.limiter.enabled = False
        fake = FakeAgent()
        main.agent = fake
        c.fake_agent = fake
        yield c
        main.limiter.enabled = True
