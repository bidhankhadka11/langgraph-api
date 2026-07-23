"""
Tests for the LangGraph ProductionAgent (app/agent.py).

The graph is exercised for real; only the LLM clients are faked, so the
primary -> fallback -> error_handler routing is genuinely tested.
"""

from tests.conftest import FakeLLM


class TestProductionAgent:
    def test_happy_path_uses_primary(self, agent):
        agent.primary_llm = FakeLLM(response="Primary says hi")

        out = agent.invoke("hello")

        assert out["model_used"] == "primary"
        assert out["response"] == "Primary says hi"
        assert out["error"] is None

    def test_fallback_path_when_primary_fails(self, agent):
        agent.primary_llm = FakeLLM(exc=RuntimeError("primary down"))
        agent.fallback_llm = FakeLLM(response="Fallback here")

        out = agent.invoke("hello")

        assert out["model_used"] == "fallback"
        assert out["response"] == "Fallback here"
        assert out["error"] is None
        # primary was tried once, fallback served the answer
        assert agent.primary_llm.calls == 1
        assert agent.fallback_llm.calls == 1

    def test_error_handler_when_both_fail(self, agent):
        agent.primary_llm = FakeLLM(exc=RuntimeError("primary down"))
        agent.fallback_llm = FakeLLM(exc=RuntimeError("fallback down"))

        out = agent.invoke("hello")

        assert out["model_used"] == "error_handler"
        assert "sorry" in out["response"].lower()
        # the last error (from the fallback attempt) is retained
        assert out["error"] is not None

    def test_max_retries_zero_skips_fallback(self, agent):
        # Documents the CLAUDE.md gotcha: max_retries gates whether the
        # fallback is even attempted. With 0, a primary failure goes straight
        # to the error handler and the fallback model is never called.
        agent.max_retries = 0
        agent.primary_llm = FakeLLM(exc=RuntimeError("primary down"))
        agent.fallback_llm = FakeLLM(response="should never be used")

        out = agent.invoke("hello")

        assert out["model_used"] == "error_handler"
        assert agent.fallback_llm.calls == 0

    def test_invoke_returns_expected_shape(self, agent):
        agent.primary_llm = FakeLLM(response="ok")

        out = agent.invoke("hello")

        assert set(out.keys()) == {"response", "model_used", "error"}
        assert isinstance(out["response"], str)
