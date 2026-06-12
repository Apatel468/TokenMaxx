# TokenMaxx — Roadmap

> **Tagline:** Maximum Intelligence, Minimum Cost  
> **Version:** 0.3.2 · **Last updated:** June 2026

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

---

## Current Milestone

**M15 — Quality & Polish**

| Task | Status |
|------|--------|
| Tune registry scores from real usage | ⬜ |
| Frontend: show original vs enhanced prompt in Chat UI | ⬜ |
| Context window truncation | ⬜ |
| `VITE_API_BASE` env for frontend | ⬜ |
| pytest suite (scorer, routing, regenerate, auth) | ⬜ |
| LLM classifier restore (optional) | ⬜ |

---

## Next Milestone

**M16 — Streaming & API Polish**

| Task | Description |
|------|-------------|
| SSE streaming | Stream Groq tokens to frontend |
| Rename `mock_response` → `response` | API cleanup |
| Mobile layout | Collapsible sidebar + analytics |
| Whisper speech-to-text UI | Use allowlisted audio model |

---

## Future Phases

- **Phase 6** — Multi-provider (OpenAI, Anthropic, Gemini)
- **Phase 7** — Rate limits, budgets, org policies
- **Phase 8** — Docker, CI/CD, Alembic, production deploy

---

## Production Readiness

**Current score:** ~65% production ready

| Area | Status |
|------|--------|
| Core routing | ✅ Allowlisted dynamic scoring |
| Model regenerate | ✅ On-demand |
| User preferences | ✅ Enhancement + model toggles |
| Authentication | ✅ JWT + roles |
| Admin visibility | ✅ Employee usage |
| Tests | ❌ None |
| Deploy | ❌ Local only |
