# TokenMaxx

**Maximum Intelligence, Minimum Cost**

TokenMaxx routes user prompts to the most cost-effective Groq model for each task, engineers prompts for better results, and tracks savings versus a premium baseline (GPT-4o).

## Features

- Task-aware model routing via `config/models.yaml`
- AI prompt engineering with rule-based fallback
- Multi-turn conversations with auto-generated titles
- Real-time analytics: cost, savings, and model usage

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- Groq API key (optional — mock mode works without it)

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux
pip install -r requirements.txt
copy .env.example .env         # add GROQ_API_KEY
uvicorn main:app --reload --port 8001
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### URLs

| Service | URL |
|---------|-----|
| App | http://localhost:5173 |
| API docs | http://127.0.0.1:8001/docs |
| Health | http://127.0.0.1:8001/health |

## Repository

https://github.com/Apatel468/smartllm-router

## Documentation

- [docs/project_memory.md](docs/project_memory.md) — project overview
- [docs/architecture.md](docs/architecture.md) — technical architecture
- [docs/system_design.md](docs/system_design.md) — system design summary
- [docs/demo_script.md](docs/demo_script.md) — demo walkthrough
- [docs/roadmap.md](docs/roadmap.md) — milestones
- [docs/decisions.md](docs/decisions.md) — architectural decisions
