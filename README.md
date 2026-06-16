# TokenMaxx

**Maximum Intelligence, Minimum Cost**

TokenMaxx routes user prompts to the most cost-effective Groq model for each task, enhances prompts with Prompt Intelligence v2, streams responses live, and tracks savings versus a premium baseline (GPT-4o).

## Features

- **LLM task classification** — Groq-powered classifier with keyword fallback
- **Prompt Intelligence Engine v2** — analyze then enhance by task type, complexity (0–100), and persona
- **SSE streaming chat** — token-by-token responses via `POST /chat/stream`
- **Task-aware routing** — complexity-aware scoring with task-specific model bonuses
- **Routing debug panel** — top 3 candidate scores, classification confidence, reason
- **Model regenerate** — retry with any top-5 model (one API call per click)
- **Model Controls** — admin org-wide + user personal toggles
- **Prompt optimization viewer** — task, complexity, persona, strategy, enhanced prompt
- **Analytics export** — `tokenmaxx-analytics-report.csv` for demos
- **Authentication** — JWT; per-user conversations and analytics
- **Admin dashboard** — employee usage metrics
- **pytest suite** — 39 tests

## Quick Start

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
