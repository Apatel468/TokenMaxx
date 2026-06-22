"""
SQLite database setup using SQLAlchemy (Phase 3).

Three tables work together:
  conversations  — one row per /chat request (a single Q&A exchange)
  messages       — user prompt + assistant response linked to a conversation
  model_runs     — routing decision, tokens, cost, and latency for each reply

Database URL is read from DATABASE_URL (Render/production) or defaults to a local
SQLite file for development.
"""

import os
from datetime import datetime, timezone
from pathlib import Path

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

DEFAULT_DATABASE_URL = "sqlite:///./smartllm_router.db"


def get_database_url() -> str:
    """Resolve DB URL from environment (Render sets DATABASE_URL)."""
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL).strip() or DEFAULT_DATABASE_URL


def get_sqlite_database_path() -> str | None:
    """Absolute path for file-based SQLite URLs; None for in-memory or non-SQLite."""
    url = get_database_url()
    if not url.startswith("sqlite:///"):
        return None
    raw_path = url.removeprefix("sqlite:///")
    if raw_path == ":memory:":
        return None
    db_path = Path(raw_path)
    if not db_path.is_absolute():
        db_path = Path.cwd() / db_path
    return str(db_path.resolve())


def _ensure_sqlite_parent_exists(url: str) -> None:
    """Create parent directories for file-based SQLite paths when needed."""
    if not url.startswith("sqlite:///"):
        return
    raw_path = url.removeprefix("sqlite:///")
    if raw_path == ":memory:":
        return
    db_path = Path(raw_path)
    if db_path.parent and str(db_path.parent) not in (".", ""):
        db_path.parent.mkdir(parents=True, exist_ok=True)


DATABASE_URL = get_database_url()
_ensure_sqlite_parent_exists(DATABASE_URL)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for all database tables."""

    pass


class User(Base):
    """
    Registered TokenMaxx account.

    role is either "user" (see own chats) or "admin" (see all usage metrics).
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="user")
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    conversations = relationship("Conversation", back_populates="owner")
    preferences = relationship(
        "UserPreference", back_populates="user", uselist=False
    )
    uploaded_documents = relationship("UploadedDocument", back_populates="owner")
    api_keys = relationship("UserApiKey", back_populates="owner")
    activity_logs = relationship("ActivityLog", back_populates="owner")


class UserPreference(Base):
    """
    Per-user app settings (prompt enhancement, future toggles).

    Missing row defaults: enhance_prompts=True.
    """

    __tablename__ = "user_preferences"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    enhance_prompts = Column(Boolean, nullable=False, default=True)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user = relationship("User", back_populates="preferences")


class Conversation(Base):
    """
    A single chat exchange (one user prompt + one AI reply).

    Phase 3A: one conversation can contain many message pairs (multi-turn).
    """

    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    # Owner of this chat thread — null only for legacy rows before auth was added
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
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

    owner = relationship("User", back_populates="conversations")
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
    # text | document | image
    content_type = Column(String(20), nullable=False, default="text")
    generation_artifact_type = Column(String(20), nullable=True)
    generation_artifact_id = Column(Integer, nullable=True)
    # Assistant only: "Router Selected" | "User Selected Model"
    response_label = Column(String(40), nullable=True)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    conversation = relationship("Conversation", back_populates="messages")


class MessageSentiment(Base):
    """
    Sentiment analysis for a user message.

    Extensible for future emotion scores, toxicity, and mood tracking.
    """

    __tablename__ = "message_sentiments"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(
        Integer, ForeignKey("messages.id"), nullable=False, unique=True, index=True
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    conversation_id = Column(
        Integer, ForeignKey("conversations.id"), nullable=False, index=True
    )
    label = Column(String(30), nullable=False)
    confidence = Column(Float, nullable=False, default=0.0)
    explanation = Column(Text, nullable=False, default="")
    method = Column(String(20), nullable=False, default="rules")
    analyzer_version = Column(String(20), nullable=False, default="v1")
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )


class AdminModelSetting(Base):
    """
    Organization-wide model toggle (admin Model Controls).

    When disabled here, the model is off for every user regardless of
    their personal preferences.
    """

    __tablename__ = "admin_model_settings"

    model_id = Column(String(100), primary_key=True)
    enabled = Column(Boolean, nullable=False, default=True)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class UserModelSetting(Base):
    """
    Per-user model preference on top of admin settings.

    Effective availability: admin_model_settings.enabled AND user_model_settings.enabled
  (missing row defaults to enabled for the user).
    """

    __tablename__ = "user_model_settings"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    model_id = Column(String(100), primary_key=True)
    enabled = Column(Boolean, nullable=False, default=True)
    explicitly_set = Column(Boolean, nullable=False, default=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


# Backward-compatible alias used in older imports
ModelSetting = AdminModelSetting


class ProviderSetting(Base):
    """
    Organization-wide provider toggle (admin Model Controls).

    When disabled, every model from that provider is unavailable for routing.
    """

    __tablename__ = "provider_settings"

    provider_name = Column(String(30), primary_key=True)
    enabled = Column(Boolean, nullable=False, default=True)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


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
    # Copied from conversation.user_id for fast admin usage reports
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    assistant_message_id = Column(
        Integer, ForeignKey("messages.id"), nullable=True
    )

    # Routing
    task_type = Column(String(50), nullable=False)
    selected_model = Column(String(100), nullable=False)
    provider = Column(String(30), nullable=False, default="groq", index=True)
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
    enhancement_method = Column(String(30), nullable=True)
    enhancement_enabled = Column(Boolean, nullable=False, default=True)
    enhancement_cost_saved = Column(Float, nullable=False, default=0.0)

    # Regeneration tracking
    is_regeneration = Column(Boolean, nullable=False, default=False)
    original_model = Column(String(100), nullable=True)
    regenerated_model = Column(String(100), nullable=True)
    turn_user_message_id = Column(Integer, ForeignKey("messages.id"), nullable=True)

    # LLM / rule-based prompt classification metadata
    classification_method = Column(String(30), nullable=True)
    classification_reason = Column(Text, nullable=True)
    classification_confidence = Column(Float, nullable=True)

    # Prompt Intelligence Engine v2 metadata
    prompt_complexity_score = Column(Integer, nullable=True)
    prompt_complexity_level = Column(String(20), nullable=True)
    prompt_persona = Column(String(100), nullable=True)
    prompt_output_format = Column(String(200), nullable=True)
    prompt_enhancement_task_type = Column(String(40), nullable=True)
    enhancement_strategy = Column(String(60), nullable=True)

    # Phase 2 RAG metadata
    rag_used = Column(Boolean, nullable=False, default=False)
    rag_chunk_count = Column(Integer, nullable=True)
    rag_source_documents = Column(Text, nullable=True)
    rag_source_filenames = Column(Text, nullable=True)

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    conversation = relationship("Conversation", back_populates="model_runs")


# ---------------------------------------------------------------------------
# Legacy table — kept so old data is not lost; new code uses tables above
# ---------------------------------------------------------------------------
class UploadedDocument(Base):
    """
    Metadata for a user-uploaded document (TXT, MD, PDF).

    Chunk text and embeddings live in ChromaDB; this table tracks ownership
    and listing metadata only.
    """

    __tablename__ = "uploaded_documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(10), nullable=False)
    chunk_count = Column(Integer, nullable=False, default=0)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    owner = relationship("User", back_populates="uploaded_documents")


class UserApiKey(Base):
    """Encrypted per-user LLM provider API keys."""

    __tablename__ = "user_api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    provider = Column(String(30), nullable=False, index=True)
    encrypted_api_key = Column(Text, nullable=False)
    key_label = Column(String(100), nullable=False, default="")
    is_active = Column(Boolean, nullable=False, default=True)
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
    last_used_at = Column(DateTime, nullable=True)

    owner = relationship("User", back_populates="api_keys")


class ActivityLog(Base):
    """Timestamped backend activity for debugging and audit."""

    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=True, index=True)
    level = Column(String(20), nullable=False, default="info", index=True)
    event_type = Column(String(60), nullable=False, index=True)
    message = Column(Text, nullable=False)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    owner = relationship("User", back_populates="activity_logs")


class GeneratedDocument(Base):
    """AI-generated downloadable document artifacts."""

    __tablename__ = "generated_documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=True, index=True)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False)
    file_size = Column(Integer, nullable=False, default=0)
    storage_path = Column(String(500), nullable=False)
    prompt = Column(Text, nullable=False)
    model_used = Column(String(100), nullable=False, default="")
    file_count = Column(Integer, nullable=False, default=1)
    is_archive = Column(Boolean, nullable=False, default=False)
    files_json = Column(Text, nullable=True)
    download_count = Column(Integer, nullable=False, default=0)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )


class GeneratedImage(Base):
    """AI-generated image artifacts."""

    __tablename__ = "generated_images"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=True, index=True)
    image_type = Column(String(60), nullable=False, default="general")
    prompt = Column(Text, nullable=False)
    provider_used = Column(String(30), nullable=False, default="openai")
    model_used = Column(String(100), nullable=False, default="dall-e-3")
    storage_path = Column(String(500), nullable=False)
    width = Column(Integer, nullable=False, default=1024)
    height = Column(Integer, nullable=False, default=1024)
    revised_prompt = Column(Text, nullable=True)
    download_count = Column(Integer, nullable=False, default=0)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )


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
    _migrate_auth_columns()
    _migrate_model_settings_tables()
    _migrate_user_model_settings_explicit_column()
    _migrate_user_preferences_table()
    _migrate_model_runs_enhancement_columns()
    _migrate_regeneration_columns()
    _migrate_classification_columns()
    _migrate_prompt_intelligence_columns()
    _migrate_rag_columns()
    _migrate_api_keys_and_logs_tables()
    _migrate_model_runs_provider_column()
    _migrate_generation_tables()
    _migrate_message_generation_columns()
    _migrate_message_sentiments_table()
    _migrate_provider_settings_table()
    _seed_model_settings()
    _seed_admin_user()


def _migrate_model_settings_tables() -> None:
    """
    Rename legacy model_settings → admin_model_settings and create user_model_settings.
    """
    with engine.connect() as conn:
        tables = {
            row[0]
            for row in conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            ).fetchall()
        }
        if "model_settings" in tables and "admin_model_settings" not in tables:
            try:
                conn.execute(
                    text("ALTER TABLE model_settings RENAME TO admin_model_settings")
                )
                conn.commit()
            except OperationalError:
                conn.rollback()
        if "user_model_settings" not in tables:
            Base.metadata.tables["user_model_settings"].create(bind=conn, checkfirst=True)
            conn.commit()


def _migrate_user_model_settings_explicit_column() -> None:
    """Track whether the user explicitly saved a model toggle."""
    with engine.connect() as conn:
        if not _table_exists(conn, "user_model_settings"):
            return
        if _table_has_column(conn, "user_model_settings", "explicitly_set"):
            return
        try:
            conn.execute(
                text(
                    "ALTER TABLE user_model_settings "
                    "ADD COLUMN explicitly_set BOOLEAN NOT NULL DEFAULT 0"
                )
            )
            conn.commit()
        except OperationalError:
            conn.rollback()


def _table_exists(conn, table_name: str) -> bool:
    tables = {
        row[0]
        for row in conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table'")
        ).fetchall()
    }
    return table_name in tables


def _seed_model_settings() -> None:
    """Insert default enabled rows for every routable model and provider."""
    from services.model_settings import seed_admin_model_settings, seed_provider_settings

    db = SessionLocal()
    try:
        seed_provider_settings(db)
        seed_admin_model_settings(db)
    finally:
        db.close()


def _migrate_provider_settings_table() -> None:
    """Create provider_settings table for org-wide provider toggles."""
    with engine.connect() as conn:
        if _table_exists(conn, "provider_settings"):
            return
        Base.metadata.tables["provider_settings"].create(bind=conn, checkfirst=True)
        conn.commit()


def _migrate_user_preferences_table() -> None:
    """Create user_preferences table for per-account settings."""
    with engine.connect() as conn:
        tables = {
            row[0]
            for row in conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            ).fetchall()
        }
        if "user_preferences" not in tables:
            Base.metadata.tables["user_preferences"].create(bind=conn, checkfirst=True)
            conn.commit()


def _migrate_model_runs_enhancement_columns() -> None:
    """Add enhancement analytics columns to model_runs."""
    new_columns = (
        ("enhancement_method", "VARCHAR(30)"),
        ("enhancement_enabled", "BOOLEAN DEFAULT 1"),
        ("enhancement_cost_saved", "FLOAT DEFAULT 0.0"),
    )
    with engine.connect() as conn:
        for column_name, column_type in new_columns:
            if _table_has_column(conn, "model_runs", column_name):
                continue
            try:
                conn.execute(
                    text(
                        f"ALTER TABLE model_runs ADD COLUMN {column_name} {column_type}"
                    )
                )
                conn.commit()
            except OperationalError:
                conn.rollback()


def _migrate_regeneration_columns() -> None:
    """Add regeneration and message label columns."""
    message_cols = (("response_label", "VARCHAR(40)"),)
    run_cols = (
        ("is_regeneration", "BOOLEAN DEFAULT 0"),
        ("original_model", "VARCHAR(100)"),
        ("regenerated_model", "VARCHAR(100)"),
        ("turn_user_message_id", "INTEGER"),
    )
    with engine.connect() as conn:
        for column_name, column_type in message_cols:
            if _table_has_column(conn, "messages", column_name):
                continue
            try:
                conn.execute(
                    text(f"ALTER TABLE messages ADD COLUMN {column_name} {column_type}")
                )
                conn.commit()
            except OperationalError:
                conn.rollback()
        for column_name, column_type in run_cols:
            if _table_has_column(conn, "model_runs", column_name):
                continue
            try:
                conn.execute(
                    text(f"ALTER TABLE model_runs ADD COLUMN {column_name} {column_type}")
                )
                conn.commit()
            except OperationalError:
                conn.rollback()


def _migrate_classification_columns() -> None:
    """Add prompt classifier metadata columns to model_runs."""
    new_columns = (
        ("classification_method", "VARCHAR(30)"),
        ("classification_reason", "TEXT"),
        ("classification_confidence", "FLOAT"),
    )
    with engine.connect() as conn:
        for column_name, column_type in new_columns:
            if _table_has_column(conn, "model_runs", column_name):
                continue
            try:
                conn.execute(
                    text(
                        f"ALTER TABLE model_runs ADD COLUMN {column_name} {column_type}"
                    )
                )
                conn.commit()
            except OperationalError:
                conn.rollback()


def _migrate_prompt_intelligence_columns() -> None:
    """Add Prompt Intelligence Engine v2 columns to model_runs."""
    new_columns = (
        ("prompt_complexity_score", "INTEGER"),
        ("prompt_complexity_level", "VARCHAR(20)"),
        ("prompt_persona", "VARCHAR(100)"),
        ("prompt_output_format", "VARCHAR(200)"),
        ("prompt_enhancement_task_type", "VARCHAR(40)"),
        ("enhancement_strategy", "VARCHAR(60)"),
    )
    with engine.connect() as conn:
        for column_name, column_type in new_columns:
            if _table_has_column(conn, "model_runs", column_name):
                continue
            try:
                conn.execute(
                    text(
                        f"ALTER TABLE model_runs ADD COLUMN {column_name} {column_type}"
                    )
                )
                conn.commit()
            except OperationalError:
                conn.rollback()


def _migrate_api_keys_and_logs_tables() -> None:
    """Create user_api_keys and activity_logs tables if missing."""
    with engine.connect() as conn:
        tables = {
            row[0]
            for row in conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            ).fetchall()
        }
        if "user_api_keys" not in tables:
            Base.metadata.tables["user_api_keys"].create(bind=conn, checkfirst=True)
            conn.commit()
        if "activity_logs" not in tables:
            Base.metadata.tables["activity_logs"].create(bind=conn, checkfirst=True)
            conn.commit()


def _migrate_rag_columns() -> None:
    """Add RAG metadata columns to model_runs."""
    new_columns = (
        ("rag_used", "BOOLEAN DEFAULT 0"),
        ("rag_chunk_count", "INTEGER"),
        ("rag_source_documents", "TEXT"),
        ("rag_source_filenames", "TEXT"),
    )
    with engine.connect() as conn:
        for column_name, column_type in new_columns:
            if _table_has_column(conn, "model_runs", column_name):
                continue
            try:
                conn.execute(
                    text(
                        f"ALTER TABLE model_runs ADD COLUMN {column_name} {column_type}"
                    )
                )
                conn.commit()
            except OperationalError:
                conn.rollback()


def _migrate_model_runs_provider_column() -> None:
    """Add provider column to model_runs for multi-provider analytics."""
    with engine.connect() as conn:
        if _table_has_column(conn, "model_runs", "provider"):
            return
        try:
            conn.execute(
                text("ALTER TABLE model_runs ADD COLUMN provider VARCHAR(30) DEFAULT 'groq'")
            )
            conn.commit()
        except OperationalError:
            conn.rollback()


def _migrate_generation_tables() -> None:
    """Create generated_documents and generated_images if missing."""
    with engine.connect() as conn:
        tables = {
            row[0]
            for row in conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            ).fetchall()
        }
        if "generated_documents" not in tables:
            Base.metadata.tables["generated_documents"].create(bind=conn, checkfirst=True)
            conn.commit()
        if "generated_images" not in tables:
            Base.metadata.tables["generated_images"].create(bind=conn, checkfirst=True)
            conn.commit()


def _migrate_message_generation_columns() -> None:
    """Add generation metadata columns to messages."""
    new_columns = (
        ("content_type", "VARCHAR(20) DEFAULT 'text'"),
        ("generation_artifact_type", "VARCHAR(20)"),
        ("generation_artifact_id", "INTEGER"),
    )
    with engine.connect() as conn:
        for column_name, column_type in new_columns:
            if _table_has_column(conn, "messages", column_name):
                continue
            try:
                conn.execute(
                    text(f"ALTER TABLE messages ADD COLUMN {column_name} {column_type}")
                )
                conn.commit()
            except OperationalError:
                conn.rollback()


def _migrate_message_sentiments_table() -> None:
    """Create message_sentiments table for per-message sentiment storage."""
    with engine.connect() as conn:
        tables = {
            row[0]
            for row in conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            ).fetchall()
        }
        if "message_sentiments" not in tables:
            Base.metadata.tables["message_sentiments"].create(bind=conn, checkfirst=True)
            conn.commit()


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


def _migrate_auth_columns() -> None:
    """Add user_id to conversations and model_runs for per-user chat isolation."""
    with engine.connect() as conn:
        if not _table_has_column(conn, "conversations", "user_id"):
            try:
                conn.execute(
                    text("ALTER TABLE conversations ADD COLUMN user_id INTEGER")
                )
                conn.commit()
            except OperationalError:
                conn.rollback()
        if not _table_has_column(conn, "model_runs", "user_id"):
            try:
                conn.execute(
                    text("ALTER TABLE model_runs ADD COLUMN user_id INTEGER")
                )
                conn.commit()
            except OperationalError:
                conn.rollback()


def _seed_admin_user() -> None:
    """Optional first admin from ADMIN_EMAIL + ADMIN_PASSWORD in .env."""
    from services.auth_service import ensure_seed_admin

    db = SessionLocal()
    try:
        ensure_seed_admin(db)
    finally:
        db.close()


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
