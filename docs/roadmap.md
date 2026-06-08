# SmartLLM Router — Roadmap

> Milestones, current focus, and path to production.  
> **Version:** 0.2.1 · **Last updated:** June 2026

---

## Completed Milestones

### M1 — MVP Backend (Phase 1)
- [x] FastAPI skeleton, keyword classifier, mock responses, cost tracking

### M2 — Frontend MVP
- [x] React + Vite, Chat UI, Analytics tab, dark styling

### M3 — LiteLLM + Groq (Phase 2)
- [x] Groq-only pivot, `.env` key, mock fallback, request logging

### M4 — Config-Driven Routing
- [x] `models.yaml`, aliases, pricing, `GET /models`

### M5 — Analytics (Phase 3)
- [x] SQLite schema, analytics endpoints, dashboard

### M6 — Conversation Memory (Phase 3A)
- [x] Multi-turn `conversation_id`, sidebar UI, full history to Groq

### M7 — Project Documentation
- [x] `docs/` folder with memory, architecture, roadmap, decisions

### M8 — LLM Classifier (Phase 3B)
- [x] Design: Groq `llama-3.1-8b-instant` classifier via LiteLLM
- [x] JSON output: task_type, difficulty, risk_level, reason
- [x] Keyword fallback when Groq unavailable
- [ ] **Restore in code:** `prompt_analyzer.py` currently keyword-only (regression)

### M9 — Prompt Engineering (Phase 4)
- [x] `prompt_enhancer.py` — AI Prompt Engineering Agent
- [x] Groq `llama-3.1-8b-instant` for enhancement (LiteLLM)
- [x] Rule-based fallback on failure
- [x] `enhancement_method`: `"ai"` | `"rule_fallback"` in API
- [x] Store `enhanced_prompt`, `system_prompt`, `enhancement_reason` in `model_runs`
- [x] `POST /chat` returns enhancement metadata
- [x] System prompt prepended in `model_clients`
- [x] Analytics history per `model_run` with `enhanced_prompt`

### M10 — GitHub
- [x] Repository: https://github.com/Apatel468/smartllm-router
- [x] Initial commit + Phase 3B/4 push

### M11 — Stabilization & UX (in progress)
- [x] Conversation titles after first reply (user + assistant, 3–8 words)
- [x] `conversations.title` column + migration
- [x] `POST /chat` returns `title`
- [x] Response cleanup (`response_cleaner.py` — Qwen thinking tags)
- [x] 100vh chat layout, 3-column UI, internal scroll
- [x] Analytics dashboard polish (KPIs, model usage, recent conversations)
- [ ] Fix `prompt_analyzer` — restore LLM classifier or add `difficulty`/`risk_level` defaults
- [ ] Frontend: show enhancement fields in Chat UI
- [ ] Context window truncation for long threads
- [ ] `VITE_API_BASE` env for frontend
- [ ] Update `main.py` docstring (port 8001)
- [ ] Remove/migrate legacy `chat_history`
- [ ] Basic pytest suite
- [ ] Store `enhancement_method` in SQLite

---

## Current Milestone

**M11 — Stabilization & UX** (see checklist above)

**Immediate priority:** Fix classifier / `AnalysisResult` so `POST /chat` pipeline is consistent with `context_builder`.

---

## Next Milestone

**M12 — Streaming & API Polish**

| Task | Description |
|------|-------------|
| SSE streaming from `/chat` | Stream Groq tokens to frontend |
| Rename `mock_response` → `response` | Breaking API cleanup |
| Typing indicator | Better UX during multi-step Groq pipeline |
| Mobile-responsive chat layout | Sidebar collapse |
| Title regeneration tool | Optional admin endpoint to clear stale titles |

---

## Future Phases

### Phase 5 — Quality & Intelligence
- Restore and tune LLM classifier permanently
- Quality scoring per model per task type
- A/B routing experiments
- User feedback (thumbs up/down)
- Move enhancer + title models to `models.yaml`

### Phase 6 — Multi-Provider
- Re-add OpenAI, Anthropic, Gemini via LiteLLM
- Provider health checks and failover

### Phase 7 — Platform
- Auth, budget limits, rate limiting, admin dashboard

### Phase 8 — Production
- Docker Compose, CI/CD, Alembic, monitoring, HTTPS

---

## Production Readiness Checklist

### Security
- [ ] Auth on mutating endpoints
- [ ] Rate limiting
- [ ] `.env` in secrets manager (prod)
- [ ] CORS restricted to production domain
- [ ] Max prompt length enforced

### Reliability
- [ ] Automated tests
- [ ] Health check includes DB
- [ ] Context truncation
- [ ] Database backups
- [ ] Classifier/enhancer pipeline regression tests

### Operations
- [ ] Alembic migrations (replace manual ALTER)
- [ ] Logging aggregation
- [ ] Runbook

### Documentation
- [x] Architecture docs (updated v0.2.1)
- [x] Handoff prompt
- [ ] API changelog
- [ ] Deployment guide

**Current score:** ~35% production ready

---

## Version History

| Version | Milestone | Summary |
|---------|-----------|---------|
| 0.1.0 | M1–M6 | MVP: Groq routing, analytics, multi-turn |
| 0.2.0 | M8–M9 | LLM classifier + AI prompt engineering agent |
| 0.2.1 | M11 (partial) | Conversation titles, UI polish, response cleanup |
| 0.3.0 | M11–M12 (planned) | Classifier fix, enhancement UI, truncation, tests, streaming |
| 1.0.0 | Phase 8 (planned) | Production-ready |

---
