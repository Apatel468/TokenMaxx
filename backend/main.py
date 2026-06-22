"""
TokenMaxx — FastAPI application entry point.

Run the server:
    cd backend
    pip install -r requirements.txt
    uvicorn main:app --reload --port 8001

Then open:
    http://127.0.0.1:8001/docs   ← interactive API docs (Swagger UI)
    http://127.0.0.1:8001/health ← health check
"""

from contextlib import asynccontextmanager
import logging
import os

from dotenv import load_dotenv

# Load backend/.env locally; on Render, variables come from the dashboard.
load_dotenv()

# Show INFO logs (LiteLLM calls, token counts, costs) in the terminal
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from database import engine, get_sqlite_database_path, init_db
from routers import (
    admin,
    analytics,
    auth,
    chat,
    conversations,
    documents,
    generations,
    logs,
    model_settings_route,
    models,
    provider_settings,
    sentiment,
    settings,
    user_api_keys,
    user_preferences,
)
from services.groq_models import sync_groq_catalog

TAGLINE = "Maximum Intelligence, Minimum Cost"
API_VERSION = "0.7.0"

_DEFAULT_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
]


def _cors_origins() -> list[str]:
    """Comma-separated CORS_ORIGINS env var, or local dev defaults."""
    raw = os.getenv("CORS_ORIGINS", "").strip()
    if not raw:
        return _DEFAULT_CORS_ORIGINS
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def _database_health() -> dict:
    """Lightweight DB probe for Render health checks."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as exc:
        logging.getLogger(__name__).warning("Database health check failed: %s", exc)
        return {"status": "error", "detail": "database_unreachable"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs once when the server starts and once when it shuts down.

    We create SQLite tables here so they're ready before the first request.
    """
    init_db()
    sync_groq_catalog(force=True)
    yield


app = FastAPI(
    title="TokenMaxx API",
    description=(
        f"{TAGLINE}. Routes user prompts to the best AI model based on task type, "
        "cost, and quality — and tracks savings vs. always using premium."
    ),
    version=API_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount feature routers (auth is public; chat/analytics/etc. require JWT)
app.include_router(auth.router)
app.include_router(user_preferences.router)
app.include_router(admin.router)
app.include_router(model_settings_route.router)
app.include_router(provider_settings.router)
app.include_router(chat.router)
app.include_router(conversations.router)
app.include_router(documents.router)
app.include_router(generations.router)
app.include_router(sentiment.router)
app.include_router(user_api_keys.router)
app.include_router(logs.router)
app.include_router(models.router)
app.include_router(analytics.router)
app.include_router(settings.router)


@app.get("/health")
def health_check():
    """
    Liveness/readiness check for Render and load balancers.

    Returns 200 when the process is up. Includes database probe status.
    """
    database = _database_health()
    overall_ok = database["status"] == "ok"
    sqlite_path = get_sqlite_database_path()
    if sqlite_path:
        database["sqlite_path"] = sqlite_path

    return {
        "status": "ok" if overall_ok else "degraded",
        "service": "TokenMaxx",
        "tagline": TAGLINE,
        "version": API_VERSION,
        "database": database,
        "groq_configured": bool(os.getenv("GROQ_API_KEY", "").strip()),
    }
