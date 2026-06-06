# SmartLLM Router — Roadmap

> Milestones, current focus, and path to production.

---

## Completed Milestones

### M1 — MVP Backend (Phase 1)
- [x] FastAPI skeleton with `/health` and `/chat`
- [x] Keyword task classifier
- [x] Hard-coded routing table (later moved to YAML)
- [x] Mock responses (no API keys required)
- [x] Cost tracking vs GPT-4o premium baseline
- [x] SQLite `chat_history` table (legacy)

### M2 — Frontend MVP
- [x] React + Vite scaffold
- [x] Chat UI: prompt input, submit, routing result display
- [x] Cost/savings display
- [x] Dark dashboard styling

### M3 — LiteLLM Integration (Phase 2, evolved)
- [x] LiteLLM dependency
- [x] Multi-provider exploration (OpenAI, Anthropic, Gemini)
- [x] **Groq-only pivot** — simplified to single provider
- [x] `GROQ_API_KEY` via `.env`
- [x] Mock fallback on missing key or errors
- [x] Request logging (model, tokens, latency, cost)

### M4 — Config-Driven Routing
- [x] `backend/config/models.yaml`
- [x] `config_loader.py` with task aliases
- [x] Pricing + premium baseline in YAML
- [x] `GET /models` from config

### M5 — Analytics (Phase 3)
- [x] New schema: `conversations`, `messages`, `model_runs`
- [x] `GET /analytics/summary`
- [x] `GET /analytics/history`
- [x] `GET /analytics/model-usage`
- [x] Frontend Analytics Dashboard tab

### M6 — Conversation Memory (Phase 3A)
- [x] `conversation_id` on POST /chat
- [x] Load prior messages → full context to Groq
- [x] `GET /conversations`, `GET /conversations/{id}`
- [x] Frontend conversation sidebar + thread UI
- [x] Multi-turn message persistence

### M7 — Project Documentation
- [x] `docs/project_memory.md`
- [x] `docs/architecture.md`
- [x] `docs/roadmap.md`
- [x] `docs/decisions.md`
- [x] Cursor handoff prompt

---

## Current Milestone

**M8 — Stabilization & Quality**

Focus: Fix known gaps before adding major features.

| Task | Priority | Status |
|------|----------|--------|
| Fix analytics for multi-turn (per model_run, not first pair only) | High | Not started |
| Context window truncation for long threads | High | Not started |
| `VITE_API_BASE` env for frontend | Medium | Not started |
| Update `main.py` docstring (port 8001) | Low | Not started |
| Remove/migrate legacy `chat_history` | Low | Not started |
| Basic pytest suite | Medium | Not started |

---

## Next Milestone

**M9 — Streaming & UX**

| Task | Description |
|------|-------------|
| SSE streaming from `/chat` | Stream Groq tokens to frontend |
| Typing indicator | Show generation in progress |
| Rename `mock_response` field | API clarity (`response` or `content`) |
| Error toasts | Better frontend error UX |
| Mobile-responsive chat layout | Sidebar collapse on small screens |

---

## Future Phases

### Phase 4 — Quality & Intelligence
- ML or LLM-based task classifier (replace keywords)
- Quality scoring per model per task type
- A/B routing experiments
- User feedback (thumbs up/down on responses)

### Phase 5 — Multi-Provider
- Re-add OpenAI, Anthropic, Gemini via LiteLLM
- Provider health checks and failover
- Cost-aware routing across providers (not just Groq)
- Bedrock for Llama 3.3 (mentioned in early plans)

### Phase 6 — Platform Features
- User authentication and per-user API keys
- Budget limits and alerts
- Admin dashboard
- Rate limiting

### Phase 7 — Production
- Docker Compose (backend + frontend + optional Postgres)
- CI/CD (GitHub Actions: lint, test, build)
- Alembic migrations
- Structured logging + monitoring
- HTTPS, secrets management (not flat `.env` in prod)

### Phase 8 — Enterprise (Optional)
- LiteLLM proxy as dedicated gateway
- Team/org billing aggregation
- SSO
- Audit logs export

---

## Production Readiness Checklist

Use this before any public deployment:

### Security
- [ ] Auth on all mutating endpoints
- [ ] Rate limiting / abuse prevention
- [ ] `.env` never in repo; secrets manager in prod
- [ ] CORS restricted to production domain
- [ ] Input sanitization / max prompt length enforced
- [ ] SQL injection review (SQLAlchemy ORM mitigates most)

### Reliability
- [ ] Automated tests (unit + integration)
- [ ] Health check includes DB connectivity
- [ ] Graceful Groq outage handling (not just mock)
- [ ] Context truncation prevents token overflow errors
- [ ] Database backups

### Operations
- [ ] Alembic migrations documented
- [ ] Logging aggregation (not just stdout)
- [ ] Error alerting
- [ ] Runbook for common failures

### Performance
- [ ] Async LLM calls or worker queue
- [ ] Connection pooling (Postgres)
- [ ] Frontend production build served via CDN/nginx

### Documentation
- [x] Architecture docs
- [x] Handoff prompt
- [ ] API changelog
- [ ] Deployment guide
- [ ] Demo script for stakeholders

### Legal / Compliance
- [ ] Data retention policy for stored prompts
- [ ] PII handling review (prompts stored in SQLite)

**Current score:** ~25% production ready (functional MVP only)

---

## Version History

| Version | Phase | Summary |
|---------|-------|---------|
| 0.1.0 | M1–M6 | MVP with Groq, analytics, multi-turn memory |
| 0.2.0 | M8 (planned) | Stabilization, tests, analytics fix |
| 0.3.0 | M9 (planned) | Streaming |
| 1.0.0 | M7 (planned) | Production-ready release |
