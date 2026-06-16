# TokenMaxx

**Maximum Intelligence, Minimum Cost**

TokenMaxx routes user prompts to the most cost-effective Groq model for each task, optionally engineers prompts for better results, and tracks savings versus a premium baseline (GPT-4o).

## Features

- **LLM task classification** — Groq-powered classifier with keyword fallback; confidence + reason in routing UI
- **Task-aware routing** — complexity-aware scoring with task-specific model bonuses (not just cheapest/fastest)
- **Routing debug panel** — top 3 candidate scores, task type, classification confidence
- **Model regenerate** — click any top-5 recommendation to retry with a different model (one API call per click)
- **Model Controls** — admin org-wide toggles + user personal preferences; intelligent fallback
- **Prompt Enhancement toggle** — user-controlled; skip enhancer to save cost/latency
- **Prompt enhancement viewer** — see original vs enhanced prompt below replies
- **Authentication** — JWT signup/login; per-user conversations and analytics
- **Admin dashboard** — employee usage metrics and cost breakdown
- **Analytics export** — download `tokenmaxx-analytics-report.csv` for demos
- Multi-turn conversations with auto-generated titles
- **pytest suite** — 30 tests covering auth, chat, routing, classifier, model settings

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- Groq API key (optional — mock mode works without it)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # add GROQ_API_KEY, JWT_SECRET
uvicorn main:app --reload --port 8001
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Tests

```bash
cd backend && source venv/bin/activate && pytest -v
```

### URLs

| Service | URL |
|---------|-----|
| App | http://localhost:5173 |
| API docs | http://127.0.0.1:8001/docs |
| Health | http://127.0.0.1:8001/health |

## Repository

https://github.com/Apatel468/TokenMaxx

## Documentation

- [docs/project_memory.md](docs/project_memory.md) — project overview
- [docs/architecture.md](docs/architecture.md) — technical architecture
- [docs/system_design.md](docs/system_design.md) — system design summary
- [docs/demo_script.md](docs/demo_script.md) — demo walkthrough
- [docs/roadmap.md](docs/roadmap.md) — milestones
- [docs/decisions.md](docs/decisions.md) — architectural decisions
