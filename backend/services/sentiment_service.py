"""
Persist and load per-message sentiment for analytics and conversation history.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from database import Conversation, Message, MessageSentiment, User
from services.conversation_store import get_conversation_or_404
from services.sentiment_analyzer import SentimentResult
from services.timezone_utils import format_timestamp_eastern


def save_message_sentiment(
    db: Session,
    *,
    user_id: int,
    message_id: int,
    conversation_id: int | None,
    result: SentimentResult,
) -> MessageSentiment:
    """Store or update sentiment for a user message."""
    message = (
        db.query(Message)
        .filter(Message.id == message_id, Message.role == "user")
        .first()
    )
    if not message:
        raise HTTPException(status_code=404, detail="User message not found.")

    conversation = get_conversation_or_404(db, message.conversation_id)
    if conversation.user_id is not None and conversation.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not your conversation.")

    resolved_conversation_id = conversation_id or message.conversation_id

    existing = (
        db.query(MessageSentiment)
        .filter(MessageSentiment.message_id == message_id)
        .first()
    )
    if existing:
        existing.label = result.label
        existing.confidence = result.confidence
        existing.explanation = result.explanation
        existing.method = result.method
        existing.analyzer_version = result.analyzer_version
        existing.conversation_id = resolved_conversation_id
        row = existing
    else:
        row = MessageSentiment(
            message_id=message_id,
            user_id=user_id,
            conversation_id=resolved_conversation_id,
            label=result.label,
            confidence=result.confidence,
            explanation=result.explanation,
            method=result.method,
            analyzer_version=result.analyzer_version,
            created_at=datetime.now(timezone.utc),
        )
        db.add(row)

    db.flush()
    return row


def get_sentiment_for_message(db: Session, message_id: int) -> MessageSentiment | None:
    return (
        db.query(MessageSentiment)
        .filter(MessageSentiment.message_id == message_id)
        .first()
    )


def get_conversation_sentiment_history(
    db: Session,
    conversation_id: int,
    user: User,
) -> list[MessageSentiment]:
    """Return sentiment rows for user messages in chronological order."""
    get_conversation_or_404(db, conversation_id, user=user)
    return (
        db.query(MessageSentiment)
        .filter(MessageSentiment.conversation_id == conversation_id)
        .order_by(MessageSentiment.created_at.asc(), MessageSentiment.id.asc())
        .all()
    )


def sentiment_row_to_dict(row: MessageSentiment) -> dict:
    return {
        "message_id": row.message_id,
        "conversation_id": row.conversation_id,
        "label": row.label,
        "confidence": round(row.confidence * 100, 1),
        "explanation": row.explanation,
        "method": row.method or "rules",
        "analyzer_version": row.analyzer_version or "v1",
        "created_at": format_timestamp_eastern(row.created_at),
    }
