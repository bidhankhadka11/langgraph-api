Tier 1 — Quick wins (a few hours each, high payoff)
1. GitHub Actions CI/CD ⭐ do this first
Add a workflow that runs pytest + linting on every push and builds the Docker image. This closes your last documented resume gap (CI/CD) truthfully, and it's maybe 30 lines of YAML. Instant "CI/CD pipeline" bullet.

2. Swap the in-memory cache for Redis
Your cache.py literally has a comment saying "in production, replace with Redis." Doing it adds Redis to your stack, makes the cache persistent across restarts and shared across instances, and gives you a real distributed-systems talking point. docker-compose already exists, so adding a Redis service is easy.

3. Make the fallback model genuinely different (multi-provider)
Right now primary and fallback are both gpt-4o-mini, so the "automatic failover" claim is thin. Point the fallback at a different model — even better, a different provider (e.g. OpenAI primary → Anthropic fallback). That turns it into a real provider-resilience story: "survives a full provider outage."

Tier 2 — Bigger upgrades (a day or two, genuinely impressive)
4. Streaming responses (SSE)
Add POST /chat/stream that streams tokens back via Server-Sent Events. This is how real LLM apps feel (ChatGPT-style typing), and it's a strong backend-skill signal.

5. Multi-turn conversation memory via LangGraph checkpointer
Your agent looks single-shot right now. Add a thread_id and wire in a LangGraph checkpointer (MemorySaver, or a Postgres/Redis checkpointer) so conversations persist. This is the headline LangGraph feature and makes it a real agent, not a passthrough.

6. API-key auth + per-key rate limiting
Add API-key authentication and key your rate limiter on the API key instead of IP. Adds "authentication/authorization" and makes the rate-limiting story much more credible for a multi-tenant service.

Tier 3 — Stretch / "wow" (pick one as a differentiator)
7. Prometheus metrics + a Grafana dashboard
Expose /metrics in Prometheus format and build a small Grafana dashboard. A screenshot of a live dashboard in your README is a huge visual credibility boost and screams "SRE/observability."

8. Load test with k6 or Locust
Run a load test and capture a real throughput number ("sustained ~X req/s at p95 < Y ms"). Gives you a hard scalability metric almost nothing in a student portfolio has.

9. Give the agent real tools (turn it into a true agent)
Add tool-calling — web search, a calculator, or a small RAG retriever over a doc set. This upgrades it from "LLM wrapper" to "agent that takes actions," which is what "AI agent" roles actually mean. Bonus: reuses your RAG experience.

10. Semantic caching
Instead of exact SHA-256 matches, embed queries and cache on cosine similarity so paraphrased questions also hit the cache. Advanced, ties in embeddings, and boosts your hit-rate metric.

My recommended path
If you want maximum resume lift for minimum time, do #1 (CI/CD) → #2 (Redis) → #3 (real multi-provider fallback) — that's a single focused session, and it completes the "production infrastructure" story end to end (tested, containerized, CI/CD'd, distributed cache, provider-resilient).

If you have a weekend and want a standout project, add #5 (conversation memory) and #7 (Grafana dashboard screenshot) on top — those two are what make an interviewer stop and say "wait, a student built this?"