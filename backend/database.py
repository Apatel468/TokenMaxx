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
    text,
)
from sqlalchemy.exc import OperationalError
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
    # Title from first user + assistant exchange (generated once after first reply)
    title = Column(String(200), nullable=True)

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

    # Phase 4 — prompt enhancement (stored for analytics/history)
    enhanced_prompt = Column(Text, nullable=True)
    system_prompt = Column(Text, nullable=True)
    enhancement_reason = Column(Text, nullable=True)

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
    _migrate_model_runs_columns()
    _migrate_conversations_columns()


def _migrate_model_runs_columns() -> None:
    """
    Add Phase 4 columns to existing SQLite databases.

    create_all() does not alter existing tables, so we run safe ALTER TABLE
    statements for databases created before prompt enhancement was added.
    """
    new_columns = (
        ("enhanced_prompt", "TEXT"),
        ("system_prompt", "TEXT"),
        ("enhancement_reason", "TEXT"),
    )
    with engine.connect() as conn:
        for column_name, column_type in new_columns:
            try:
                conn.execute(
                    text(
                        f"ALTER TABLE model_runs ADD COLUMN {column_name} {column_type}"
                    )
                )
                conn.commit()
            except OperationalError:
                # Column already exists — safe to ignore
                conn.rollback()


def _table_has_column(conn, table: str, column: str) -> bool:
    rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return any(row[1] == column for row in rows)


def _migrate_conversations_columns() -> None:
    """Add title column to conversations for existing SQLite databases."""
    with engine.connect() as conn:
        if _table_has_column(conn, "conversations", "title"):
            return
        try:
            conn.execute(
                text("ALTER TABLE conversations ADD COLUMN title VARCHAR(200)")
            )
            conn.commit()
        except OperationalError:
            conn.rollback()


def get_db():
    """FastAPI dependency — yields a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
