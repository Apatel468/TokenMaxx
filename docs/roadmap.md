# TokenMaxx — Roadmap

> **Tagline:** Maximum Intelligence, Minimum Cost  
> **Version:** 0.3.1 · **Last updated:** June 2026

---

## Completed Milestones

### M1–M11
- [x] MVP backend, frontend, Groq/LiteLLM, analytics, multi-turn memory, docs, TokenMaxx rebrand

### M12 — Dynamic Router & Model Controls (v0.3.0)
- [x] `model_registry.py` — metadata for all Groq chat models
- [x] `groq_models.py` — Groq API catalog sync + missing-model logging
- [x] `model_scorer.py` — composite routing formula
- [x] Model Controls UI + settings API
- [x] Fallback when preferred model disabled
- [x] `routing_score` + `candidate_models` in chat response
- [x] Analytics layout fix (no horizontal scroll)

### M13 — Auth & Admin (v0.3.1)
- [x] JWT signup/login/logout/me (bcrypt + PyJWT)
- [x] Protected routes — chat, analytics, conversations, models
- [x] Per-user conversations and `model_runs.user_id`
- [x] Two-tier model settings (`admin_model_settings` + `user_model_settings`)
- [x] Unified `GET/PUT /model-settings` API
- [x] Admin dashboard — `GET /admin/employee-usage`
- [x] Frontend Login, Signup, Admin tab, `authFetch` HTTP layer
- [x] Optional admin seed via `ADMIN_EMAIL` / `ADMIN_PASSWORD`

---

## Current Milestone

**M14 — Quality & Polish**

| Task | Status |
|------|--------|
| Tune registry scores from real usage | ⬜ |
| Frontend: show enhancement fields in Chat UI | ⬜ |
| Context window truncation | ⬜ |
| `VITE_API_BASE` env for frontend | ⬜ |
| pytest suite (scorer, routing, settings, auth) | ⬜ |
| LLM classifier restore (optional) | ⬜ |

---

## Next Milestone

**M15 — Streaming & API Polish**

| Task | Description |
|------|-------------|
| SSE streaming | Stream Groq tokens to frontend |
| Rename `mock_response` → `response` | API cleanup |
| Mobile layout | Collapsible sidebar + analytics |
| Token refresh / revoke | Optional server-side session management |

---

## Future Phases

- **Phase 6** — Multi-provider (OpenAI, Anthropic, Gemini)
- **Phase 7** — Rate limits, budgets, org policies
- **Phase 8** — Docker, CI/CD, Alembic, production deploy

---

## Production Readiness

**Current score:** ~60% production ready

| Area | Status |
|------|--------|
| Core routing | ✅ Dynamic scoring |
| Model catalog | ✅ Registry + API sync |
| User preferences | ✅ Two-tier Model Controls |
| Authentication | ✅ JWT + roles |
| Admin visibility | ✅ Employee usage |
| Tests | ❌ None |
| Deploy | ❌ Local only |
