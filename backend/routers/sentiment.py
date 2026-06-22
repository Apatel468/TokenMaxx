"""
Sentiment analysis API — async classification without blocking chat.
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import User, get_db
from models import (
    SentimentAnalyzeRequest,
    SentimentHistoryResponse,
    SentimentOut,
    SentimentStoreRequest,
)
from services.auth_dependencies import get_current_user
from services.sentiment_analyzer import analyze_sentiment, unknown_sentiment_result
from services.sentiment_service import (
    get_conversation_sentiment_history,
    save_message_sentiment,
    sentiment_row_to_dict,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sentiment", tags=["sentiment"])


def _result_to_out(
    result,
    *,
    message_id: int | None = None,
    conversation_id: int | None = None,
    created_at: str | None = None,
) -> SentimentOut:
    confidence_pct = round(float(result.confidence) * 100, 1)
    if result.method == "error":
        confidence_pct = 0.0
    return SentimentOut(
        label=result.label,
        confidence=confidence_pct,
        explanation=result.explanation,
        method=result.method,
        message_id=message_id,
        conversation_id=conversation_id,
        created_at=created_at,
    )


@router.post("/analyze", response_model=SentimentOut)
async def analyze_sentiment_endpoint(
    request: SentimentAnalyzeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Analyze message sentiment asynchronously (runs in a thread pool).

    Optionally persists when message_id is provided.
    """
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text is required.")

    try:
        result = await asyncio.to_thread(analyze_sentiment, text)
    except Exception as exc:
        logger.warning("Sentiment analyze failed: %s", exc)
        return _result_to_out(
            unknown_sentiment_result(),
            conversation_id=request.conversation_id,
        )

    created_at = None
    message_id = request.message_id
    if message_id:
        row = save_message_sentiment(
            db,
            user_id=current_user.id,
            message_id=message_id,
            conversation_id=request.conversation_id,
            result=result,
        )
        db.commit()
        message_id = row.message_id
        created_at = sentiment_row_to_dict(row)["created_at"]

    return _result_to_out(
        result,
        message_id=message_id,
        conversation_id=request.conversation_id,
        created_at=created_at,
    )


@router.post("/store", response_model=SentimentOut)
def store_sentiment_endpoint(
    request: SentimentStoreRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Attach a previously computed sentiment result to a saved user message."""
    from services.sentiment_analyzer import SentimentResult

    result = SentimentResult(
        label=request.label,
        confidence=round(request.confidence / 100.0, 4),
        explanation=request.explanation,
        method=request.method,
    )
    row = save_message_sentiment(
        db,
        user_id=current_user.id,
        message_id=request.message_id,
        conversation_id=request.conversation_id,
        result=result,
    )
    db.commit()
    payload = sentiment_row_to_dict(row)
    return SentimentOut(**payload)


@router.get(
    "/conversations/{conversation_id}/history",
    response_model=SentimentHistoryResponse,
)
def conversation_sentiment_history(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Sentiment trend history for a conversation (chronological)."""
    rows = get_conversation_sentiment_history(db, conversation_id, current_user)
    items = [SentimentOut(**sentiment_row_to_dict(row)) for row in rows]
    return SentimentHistoryResponse(conversation_id=conversation_id, items=items)
