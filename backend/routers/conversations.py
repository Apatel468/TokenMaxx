"""
Conversations router — list and load multi-turn chat threads (Phase 3A).

GET /conversations       → recent conversation summaries
GET /conversations/{id}  → full message history for one thread
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import ConversationDetail, ConversationListItem
from services.conversation_store import get_conversation_detail, list_conversations

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationListItem])
def get_conversations(
    limit: int = 50,
    db: Session = Depends(get_db),
) -> list[ConversationListItem]:
    """List recent conversations (newest activity first)."""
    return list_conversations(db, limit=limit)


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
) -> ConversationDetail:
    """Return all messages in a conversation, oldest first."""
    return get_conversation_detail(db, conversation_id)
