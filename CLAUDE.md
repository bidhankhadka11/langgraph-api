# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this is

A production-ready **FastAPI + LangGraph chat API**. A single `POST /chat` endpoint takes a user
message and returns an LLM answer, wrapped in production concerns: input/output security, response
caching, rate limiting, retries/fallback, structured logging, metrics, and LangSmith tracing.

Despite the repo name ("RAG Production"), there is **no retrieval/vector-store layer yet** — it is
currently an LLM chat service with production scaffolding. Retrieval would be added inside the agent.

## Commands

Uses **uv** for dependency management (Python >=3.11).

```bash
uv sync                                          # install deps (incl. dev group)
uv run uvicorn app.main:app --reload             # run dev server on :8000
uv run pytest                                    # run tests
uv run pytest tests/test_security.py -v          # run one test file

# Docker (see Dockerfile — runs uvicorn on :8000, non-root, with healthcheck)
docker build -t rag-production . && docker run -p 8000:8000 --env-file .env rag-production
```

Interactive API docs at `http://localhost:8000/docs` once running.

## Architecture

Request flow through `POST /chat` (see [app/main.py](app/main.py) `chat()`):

```
request → SecurityPipeline.check_input()   # injection block + delimiter clean + PII mask
        → ResponseCache.get()              # return early on hit
        → ProductionAgent.invoke()         # primary model → fallback on failure → graceful error
        → SecurityPipeline.check_output()  # PII mask + harmful-content block
        → ResponseCache.set() + MetricsCollector.record_request()
        → ChatResponse
```

Components are created once in the FastAPI **lifespan** (startup) and held as module globals in
`main.py`. Endpoints: `POST /chat`, `GET /health`, `GET /metrics`, `GET /cache/stats`.

### Module map (`app/`)

| File | Responsibility |
|------|----------------|
| `config.py` | `Settings` (pydantic-settings) + cached `get_settings()`. Calls `load_dotenv()` on import. |
| `models.py` | Pydantic request/response contracts (`ChatRequest`, `ChatResponse`, `HealthResponse`, `MetricsResponse`, `ErrorResponse`). |
| `security.py` | `InputSanitizer`, `PIIDetector`, `OutputValidator`, and `SecurityPipeline` (the single class wired into the API). |
| `cache.py` | `ResponseCache` — in-memory TTL cache keyed by SHA-256 of the normalized query. Swap for Redis in real prod. |
| `monitoring.py` | `JSONFormatter` + `get_logger()` (structured JSON logs), `MetricsCollector`, `RequestTimer`. |
| `agent.py` | `AgentState` (TypedDict) + `ProductionAgent` — a LangGraph state machine with primary→fallback→error routing. |
| `main.py` | FastAPI app, lifespan wiring, rate limiting (slowapi), exception handlers, endpoints. |

## Conventions & key APIs

- **Config is env-driven.** All tunables come from `.env` via `get_settings()` (see `.env.example`).
  Read config through `get_settings()`, not `os.getenv`.
- **`MetricsCollector`** (thread-safe): `record_request(latency_ms, *, input_tokens=0, output_tokens=0, cached=False, error=False)`,
  `snapshot()` (dict matching `MetricsResponse`), `reset()`. Note the kwarg is `cached`, not `cache_hit`.
- **`SecurityPipeline`**: `check_input(text) -> (is_allowed, cleaned_text, notes)` and
  `check_output(text) -> (cleaned_output, warnings)`.
- **`ProductionAgent.invoke(message) -> {"response", "model_used", "error"}`**. `model_used` is one of
  `"primary" | "fallback" | "error_handler"`.
- **Logging**: use `logger.info(msg, extra={"extra_data": {...}})` — `JSONFormatter` emits JSON for aggregators.

## Gotchas (learned the hard way)

- **LLM provider is currently OpenAI, not Anthropic.** `config.py` uses `openai_api_key` + `gpt-4o-mini`
  and `agent.py` imports `ChatOpenAI`, even though `langchain-anthropic` is installed and `.env` also has
  an `ANTHROPIC_API_KEY`. Pick one deliberately before extending the agent. To switch to Claude: swap to
  `ChatAnthropic`, rename the config field, and use a Claude model id (e.g. `claude-opus-4-8`).
- **LangSmith tracing depends on `load_dotenv()` in `config.py`.** pydantic-settings loads `.env` into the
  `Settings` object only; the LangSmith SDK reads `os.environ` directly. Without `load_dotenv()`, tracing is
  silently off. Don't remove that call.
- **Config field names vs `.env` names diverge.** `config.py` fields are `langchain_*` (→ `LANGCHAIN_*` env
  vars) but `.env` uses `LANGSMITH_*`. Tracing still works (SDK accepts both prefixes from `os.environ`), but
  `settings.langchain_api_key` stays empty. Don't rely on that field for the key.
- **Token counts in `/chat` are estimates**, not a real tokenizer — `len(text.split()) * 1.3`. Fine for rough
  metrics; replace with the provider's tokenizer if you need accuracy.
- **`ProductionAgent` "retry" is try-once-then-fallback**, not N primary retries — there's no edge looping back
  to the `process` node, so `max_retries` only gates whether the fallback model is attempted.
- **State is per-process and resets on restart** — both `ResponseCache` and `MetricsCollector` are in-memory
  and per-instance. Use Redis / a metrics backend for multi-instance or persistent deployments.

## Testing

Tests live in `tests/` and run under pytest. Prefer testing component logic with **fake LLMs** (inject a stub
with an `invoke()` method into `ProductionAgent`) so tests stay fast, deterministic, and don't spend tokens —
only make real API calls in an explicitly-marked smoke test.
