# TokenMaxx — Roadmap

> **Tagline:** Maximum Intelligence, Minimum Cost  
> **Version:** 0.4.0 · **Last updated:** June 2026

---

## Completed Milestones

### M1–M14
- [x] MVP through auth, admin, regenerate, allowlist, analytics (see prior releases)

### M15 — Quality & Polish (v0.3.3)
- [x] LLM task classifier + keyword fallback
- [x] Task-aware routing (complexity score, dynamic weights, task bonuses)
- [x] Top-3 candidate scores in routing panel
- [x] Prompt enhancement viewer (original vs enhanced)
- [x] Model settings sync (`explicitly_set`)
- [x] pytest suite + analytics CSV export

### M16 — Streaming & Prompt Intelligence (v0.4.0)
- [x] SSE streaming — `POST /chat/stream` with `routing_start`, `routing_complete`, `token`, `complete`, `error`
- [x] Real Groq streaming via LiteLLM; word-by-word fallback
- [x] Frontend live token display + typing cursor
- [x] Prompt Intelligence Engine v2 — analyze then enhance by task, complexity, persona
- [x] `PromptAnalysis` metadata in API + UI (task, complexity, persona, strategy)
- [x] Clean enhanced prompts (no internal bracket notes)
- [x] Tests: `test_chat_stream.py`, `test_prompt_intelligence.py` (39 total)

---

## Current Milestone

**M17 — API Polish & Production Prep**

| Task | Status |
|------|--------|
| Rename `mock_response` → `response` | ⬜ |
| Context window truncation | ⬜ |
| `VITE_API_BASE` env for frontend | ⬜ |
| Mobile layout | ⬜ |
| Analytics PDF export | ⬜ |
| Streaming regenerate | ⬜ |
| Tune registry scores from real usage | ⬜ |
| Whisper speech-to-text UI | ⬜ |

---

## Future Phases

- **Phase 6** — Multi-provider (OpenAI, Anthropic, Gemini)
- **Phase 7** — Rate limits, budgets, org policies
- **Phase 8** — Docker, CI/CD, Alembic, production deploy

---

## Production Readiness

**Current score:** ~80% production ready

| Area | Status |
|------|--------|
| Core routing | ✅ Task-aware complexity scoring |
| Prompt Intelligence | ✅ v2 analyze + enhance |
| Streaming chat | ✅ SSE `/chat/stream` |
| Task classification | ✅ LLM + keyword fallback |
| Model regenerate | ✅ On-demand (non-streaming) |
| Authentication | ✅ JWT + roles |
| Analytics export | ✅ CSV (client-side) |
| Tests | ✅ 39 pytest tests |
| Deploy | ❌ Local only |
