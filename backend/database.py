"""
SQLite database setup using SQLAlchemy (Phase 3).

Three tables work together:
  conversations  — one row per /chat request (a single Q&A exchange)
  messages       — user prompt + assistant response linked to a conversation
  model_runs     — routing decision, tokens, cost, and latency for each reply

SQLite stores everything in smartllm_router.db — no extra setup needed.
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker

DATABASE_URL = "sqlite:///./smartllm_router.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for all database tables."""

    pass


class Conversation(Base):
    """
    A single chat exchange (one user prompt + one AI reply).

    Phase 3A: one conversation can contain many message pairs (multi-turn).
    """

    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    messages = relationship("Message", back_populates="conversation")
    model_runs = relationship("ModelRun", back_populates="conversation")


class Message(Base):
    """
    One message in a conversation — either from the user or the assistant.

    role: "user" for the prompt, "assistant" for the model response.
    """

    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(
        Integer, ForeignKey("conversations.id"), nullable=False, index=True
    )
    role = Column(String(20), nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    conversation = relationship("Conversation", back_populates="messages")


class ModelRun(Base):
    """
    Routing decision and cost metrics for one AI reply.

    Linked to the conversation and the assistant message that was generated.
    """

    __tablename__ = "model_runs"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(
        Integer, ForeignKey("conversations.id"), nullable=False, index=True
    )
    assistant_message_id = Column(
        Integer, ForeignKey("messages.id"), nullable=True
    )

    # Routing
    task_type = Column(String(50), nullable=False)
    selected_model = Column(String(100), nullable=False)
    reason_selected = Column(Text, nullable=False)

    # Token usage
    input_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)

    # Cost metrics (USD)
    estimated_cost = Column(Float, nullable=False)
    premium_model_cost = Column(Float, nullable=False)
    savings_usd = Column(Float, nullable=False)
    savings_percentage = Column(Float, nullable=False)

    # Performance
    latency_ms = Column(Float, nullable=False, default=0.0)
    is_mock = Column(Boolean, nullable=False, default=False)

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    conversation = relationship("Conversation", back_populates="model_runs")


# ---------------------------------------------------------------------------
# Legacy table — kept so old data is not lost; new code uses tables above
# ---------------------------------------------------------------------------
class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, index=True)
    prompt = Column(String, nullable=False)
    task_type = Column(String, nullable=False)
    selected_model = Column(String, nullable=False)
    estimated_actual_cost = Column(Float, nullable=False)
    estimated_premium_cost = Column(Float, nullable=False)
    estimated_savings_percentage = Column(Float, nullable=False)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


def init_db() -> None:
    """Create all tables if they don't exist yet. Called on app startup."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency — yields a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
