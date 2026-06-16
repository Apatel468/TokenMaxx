# TokenMaxx — Roadmap

> **Tagline:** Maximum Intelligence, Minimum Cost  
> **Version:** 0.3.3 · **Last updated:** June 2026

---

## Completed Milestones

### M1–M11
- [x] MVP backend, frontend, Groq/LiteLLM, analytics, multi-turn memory, docs, TokenMaxx rebrand

### M12 — Dynamic Router & Model Controls (v0.3.0)
- [x] Composite scoring router, Model Controls UI, fallback routing, routing_score in chat response

### M13 — Auth & Admin (v0.3.1)
- [x] JWT auth, per-user data, two-tier model settings, unified `/model-settings`, admin dashboard

### M14 — Preferences, Regenerate & Allowlist (v0.3.2)
- [x] User prompt enhancement toggle (`GET/PUT /user/preferences`)
- [x] `POST /chat/regenerate` — on-demand model retry (one LLM call per click)
- [x] Top-5 recommendations in routing panel with availability + disabled reasons
- [x] Groq model allowlist (6 chat + whisper audio-only)
- [x] Stale SQLite model settings cleanup on startup
- [x] Regenerated message UI: "User switched model to …"
- [x] Analytics UI simplified (cost/savings focus; enhancement/regen metrics hidden)

### M15 — Quality & Polish (v0.3.3)
- [x] LLM task classifier (`llm_classifier.py`) with keyword fallback
- [x] Task-aware routing — complexity score, dynamic weights, task-specific bonuses
- [x] Top-3 candidate scores in Latest Routing panel for debugging
- [x] Classification confidence + reason in routing UI
- [x] Prompt enhancement viewer (original vs enhanced prompt)
- [x] Model settings sync fix (`explicitly_set`, `sync_user_model_settings`)
- [x] pytest suite — auth, chat, classifier, routing, model settings (30 tests)
- [x] Analytics CSV export (`tokenmaxx-analytics-report.csv`)

---

## Current Milestone

**M16 — Streaming & API Polish**

| Task | Status |
|------|--------|
| SSE streaming | ⬜ |
| Rename `mock_response` → `response` | ⬜ |
| Context window truncation | ⬜ |
| `VITE_API_BASE` env for frontend | ⬜ |
| Mobile layout | ⬜ |
| Analytics PDF export | ⬜ |
| Tune registry scores from real usage | ⬜ |
| Whisper speech-to-text UI | ⬜ |

---

## Future Phases

- **Phase 6** — Multi-provider (OpenAI, Anthropic, Gemini)
- **Phase 7** — Rate limits, budgets, org policies
- **Phase 8** — Docker, CI/CD, Alembic, production deploy

---

## Production Readiness

**Current score:** ~75% production ready

| Area | Status |
|------|--------|
| Core routing | ✅ Task-aware complexity scoring |
| Task classification | ✅ LLM + keyword fallback |
| Model regenerate | ✅ On-demand |
| User preferences | ✅ Enhancement + model toggles |
| Authentication | ✅ JWT + roles |
| Admin visibility | ✅ Employee usage |
| Analytics export | ✅ CSV (client-side) |
| Tests | ✅ 30 pytest tests |
| Deploy | ❌ Local only |
