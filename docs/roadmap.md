# SmartLLM Router — Roadmap

> Milestones, current focus, and path to production.  
> **Version:** 0.2.2 · **Last updated:** June 2026

---

## Completed Milestones

### M1–M7
- [x] MVP backend, frontend, Groq/LiteLLM, YAML routing, analytics, multi-turn memory, docs

### M8 — LLM Classifier (Phase 3B)
- [x] Design + `models.yaml` classifier block
- [x] Keyword fallback
- [ ] **Optional:** Restore Groq classifier in `prompt_analyzer.py` (keyword + defaults work today)

### M9 — Prompt Engineering (Phase 4)
- [x] AI prompt engineering agent + rule fallback
- [x] Enhancement metadata in API and `model_runs`

### M10 — GitHub
- [x] https://github.com/Apatel468/smartllm-router

### M11 — Stabilization & UX
- [x] Conversation titles (after first reply, user + assistant)
- [x] Response cleanup (Qwen thinking tags)
- [x] 100vh 3-column chat UI + analytics polish
- [x] `POST /chat` returns `title`
- [x] Keyword analyzer defaults (`difficulty`, `risk_level`)
- [x] Groq YAML routing restored in `router_engine.py`
- [x] `cost_tracker` YAML pricing + `log_request_metrics`
- [x] CORS for ports 5173 and 5174
- [ ] Frontend: show enhancement fields in Chat UI
- [ ] Context window truncation
- [ ] `VITE_API_BASE` env for frontend
- [ ] Update `main.py` docstring (port 8001)
- [ ] pytest suite
- [ ] Store `enhancement_method` in SQLite
- [ ] Commit + push latest pipeline fixes to GitHub

---

## Current Milestone

**M11 — Stabilization & UX**

App is runnable end-to-end. Remaining M11 items are UX, tests, and polish.

---

## Next Milestone

**M12 — Streaming & API Polish**

| Task | Description |
|------|-------------|
| SSE streaming | Stream Groq tokens to frontend |
| Rename `mock_response` → `response` | API cleanup |
| LLM classifier restore | Optional Groq classify step |
| Title regeneration endpoint | Clear stale titles |
| Mobile layout | Collapsible sidebar |

---

## Future Phases

- **Phase 5** — Quality scoring, A/B routing, move enhancer/title models to YAML
- **Phase 6** — Multi-provider (OpenAI, Anthropic, Gemini)
- **Phase 7** — Auth, rate limits, budgets
- **Phase 8** — Docker, CI/CD, Alembic, production deploy

---

## Production Readiness

**Current score:** ~40% production ready

| Area | Status |
|------|--------|
| Core pipeline | ✅ Works locally |
| Documentation | ✅ Updated v0.2.2 |
| Tests | ❌ None |
| Auth / rate limits | ❌ None |
| Alembic | ❌ Manual ALTER only |
| Deployment guide | ❌ Not written |

---

## Version History

| Version | Summary |
|---------|---------|
| 0.1.0 | MVP: Groq routing, analytics, multi-turn |
| 0.2.0 | LLM classifier design + AI prompt engineering |
| 0.2.1 | Conversation titles, UI polish, response cleanup |
| 0.2.2 | Pipeline fixes (router, cost_tracker, CORS, analyzer defaults) |
| 0.3.0 | Planned: enhancement UI, tests, streaming |

---
