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

from dotenv import load_dotenv

# Load API keys from backend/.env before anything else imports model_clients
load_dotenv()

# Show INFO logs (LiteLLM calls, token counts, costs) in the terminal
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
from routers import analytics, chat, conversations, models

TAGLINE = "Maximum Intelligence, Minimum Cost"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs once when the server starts and once when it shuts down.

    We create SQLite tables here so they're ready before the first request.
    """
    init_db()
    yield


app = FastAPI(
    title="TokenMaxx API",
    description=(
        f"{TAGLINE}. Routes user prompts to the best AI model based on task type, "
        "cost, and quality — and tracks savings vs. always using premium."
    ),
    version="0.2.2",
    lifespan=lifespan,
)

# Allow the React frontend (different port) to call this API during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount feature routers
app.include_router(chat.router)
app.include_router(conversations.router)
app.include_router(models.router)
app.include_router(analytics.router)


@app.get("/health")
def health_check():
    """
    Simple liveness check.

    Returns 200 with a JSON body so load balancers and the frontend
    can confirm the API is running.
    """
    return {
        "status": "ok",
        "service": "TokenMaxx",
        "tagline": TAGLINE,
        "version": "0.2.2",
    }
