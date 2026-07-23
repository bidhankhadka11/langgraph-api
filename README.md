# Production LangGraph API

[![CI](https://github.com/bidhankhadka11/langgraph-api/actions/workflows/ci.yml/badge.svg)](https://github.com/bidhankhadka11/langgraph-api/actions/workflows/ci.yml)

A production-grade **LLM chat API** built with FastAPI and LangGraph — designed to show what it takes
to run a language-model service in production, not just call an LLM in a notebook.

A single `POST /chat` endpoint turns a user message into an LLM answer, wrapped with the concerns real
deployments need: input/output security, response caching, rate limiting, model fallback, structured
logging, metrics, and distributed tracing.

> **Note:** This is a backend API only — there's no UI. Interact with it via the endpoints below or the
> auto-generated Swagger docs at `/docs`.

**Live:** `https://langgraph-api-dkzi.onrender.com/docs` (Dockerized, hosted on [Render](https://render.com)) · **Docs:** [`/docs`](https://production-langgraph-api.onrender.com/docs)

---

## Features

- **🧠 LangGraph agent** — a state-machine agent with automatic **cross-provider model fallback**: if the
  primary model (OpenAI `gpt-4o-mini`) fails, it retries on a different provider (Anthropic Claude Haiku 4.5)
  for resilience, and degrades gracefully to a friendly error instead of a 500.
- **🛡️ Security pipeline** — blocks prompt-injection attempts, strips risky delimiters, and masks PII
  (emails, phones, SSNs, credit cards) on both the way in *and* the way out. Output is also scanned for
  leaked secrets and harmful content.
- **⚡ Response caching** — in-memory TTL cache (SHA-256 keyed, case-insensitive) so repeat questions
  skip the LLM entirely.
- **🚦 Rate limiting** — per-client request throttling via slowapi.
- **📊 Observability** — structured JSON logs, a live `/metrics` endpoint (latency, error rate, cache hit
  rate, token usage), and full **LangSmith tracing** of every agent call.
- **❤️ Health checks** — `/health` endpoint wired to the Docker/Render healthcheck.

## Architecture

Every `POST /chat` request flows through the pipeline:

```
                       ┌──────────────────────────────────────────────┐
   client  ──POST /chat──▶  1. Security check   (injection + PII mask) │
                       │   2. Cache lookup      (return early on hit)  │
                       │   3. LangGraph agent   (primary → fallback)   │
                       │   4. Output validation (PII + harmful scan)   │
                       │   5. Cache store  +  6. Metrics / tracing     │
                       └──────────────────────────────────────────────┘
                                          │
                                    ChatResponse
```

Components are initialized once at startup via FastAPI's lifespan and shared across requests.

## Tech Stack

| Concern | Tool |
|---------|------|
| Web framework | FastAPI + Uvicorn |
| Agent orchestration | LangGraph + LangChain |
| LLM provider | OpenAI (`gpt-4o-mini`) primary, Anthropic (`claude-haiku-4-5`) fallback |
| Tracing / observability | LangSmith |
| Rate limiting | slowapi |
| Config / validation | pydantic-settings |
| Packaging | uv |
| Deployment | Docker → Render |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/chat` | Send a message, get an LLM response |
| `GET`  | `/health` | Health check (used by Docker/Render) |
| `GET`  | `/metrics` | Operational metrics (latency, errors, cache, tokens) |
| `GET`  | `/cache/stats` | Cache hit/miss statistics |
| `GET`  | `/docs` | Interactive Swagger UI |

### Example

```bash
curl -X POST https://production-langgraph-api.onrender.com/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is retrieval-augmented generation?", "thread_id": "demo"}'
```

```json
{
  "response": "Retrieval-augmented generation is a technique that combines information retrieval with text generation...",
  "thread_id": "demo",
  "model_used": "primary",
  "cached": false,
  "processing_time_ms": 1484.2,
  "security_notes": [],
  "timestamp": "2026-07-22T10:00:00+00:00"
}
```

## Running Locally

Requires Python 3.11+ and [uv](https://github.com/astral-sh/uv).

```bash
# 1. Clone
git clone git@github.com:bidhankhadka11/langgraph-api.git
cd langgraph-api

# 2. Configure environment
cp .env.example .env      # then fill in your API keys

# 3. Install dependencies
uv sync

# 4. Run the dev server (http://localhost:8000)
uv run uvicorn app.main:app --reload
```

### With Docker

```bash
docker compose up --build      # serves on http://localhost:8000
```

## Environment Variables

Copy `.env.example` to `.env` and fill in:

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key — primary model (**required**) | — |
| `ANTHROPIC_API_KEY` | Anthropic API key — fallback model (required for fallback) | — |
| `PRIMARY_MODEL` | Primary model id (OpenAI) | `gpt-4o-mini` |
| `FALLBACK_MODEL` | Fallback model id (Anthropic) | `claude-haiku-4-5` |
| `LANGSMITH_API_KEY` | LangSmith key (enables tracing) | — |
| `LANGSMITH_PROJECT` | LangSmith project name | `production-api` |
| `APP_ENV` | `development` / `production` | `development` |
| `RATE_LIMIT` | Requests per client | `20/minute` |
| `CACHE_TTL_SECONDS` | Cache entry lifetime | `300` |
| `MAX_RETRIES` | Agent retry budget | `3` |

> `.env` is gitignored — never commit real secrets. On Render, set them as service environment variables.

## Testing

```bash
uv run pytest                                    # run the suite
uv run pytest --cov=app --cov-report=term-missing  # with coverage
```

**61 tests, 100% line coverage** — fast, deterministic, and offline. The LLM clients
(`ChatOpenAI` / `ChatAnthropic`) are replaced with a deterministic `FakeLLM`, and LangSmith
tracing is disabled in tests, so the suite spends no API tokens and makes no network calls.

Coverage spans every layer:

- **Agent** — the LangGraph state machine's `primary → fallback → error_handler` routing
  (fallback fires only when the primary fails and `max_retries` allows it).
- **API** — the full `/chat` pipeline via `TestClient`: cache miss-then-hit (a repeat query is
  served from cache without re-invoking the agent), prompt-injection blocking, PII masking on
  input and output, rate limiting (429), and validation errors (422).
- **Security, cache, monitoring, models, config** — component logic asserted in isolation.

Shared fixtures and fakes live in [tests/conftest.py](tests/conftest.py).

## Project Structure

```
app/
├── main.py         # FastAPI app, routes, lifespan wiring
├── agent.py        # LangGraph agent (primary → fallback → error)
├── security.py     # InputSanitizer, PIIDetector, OutputValidator, SecurityPipeline
├── cache.py        # In-memory TTL response cache
├── monitoring.py   # JSON logging, MetricsCollector, RequestTimer
├── config.py       # pydantic-settings configuration
└── models.py       # Pydantic request/response models
tests/              # pytest suite (conftest fakes + per-module tests)
├── conftest.py     # FakeLLM / FakeAgent fixtures, dummy keys, tracing off
├── test_agent.py   # LangGraph routing: primary → fallback → error_handler
├── test_api.py     # /chat pipeline, health/metrics/cache endpoints, rate limit
├── test_security.py, test_cache.py, test_monitoring.py, test_models.py, test_config.py
Dockerfile          # Container image (non-root, healthcheck)
render.yml          # Render infrastructure-as-code
```

## Deployment

Deployed to Render as a Dockerized web service with `autoDeploy` on push to `main`. Infrastructure is
defined in [`render.yml`](render.yml); the container is built from the [`Dockerfile`](Dockerfile) (runs
as a non-root user with a `/health` healthcheck). The same image runs locally via `docker compose`.

## Roadmap

- [ ] Add a retrieval layer (vector store) to make it a true RAG service
- [ ] Persistent, shared cache (Redis) for multi-instance deploys
- [ ] Real tokenizer-based token counting
- [ ] A minimal web UI

## License

MIT
