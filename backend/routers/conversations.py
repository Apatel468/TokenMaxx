"""
Conversations router — list and load multi-turn chat threads (Phase 3A).

GET /conversations       → recent conversation summaries (own threads only)
GET /conversations/{id}  → full message history for one thread
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import User, get_db
from models import ConversationDetail, ConversationListItem
from services.auth_dependencies import get_current_user
from services.conversation_store import get_conversation_detail, list_conversations

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationListItem])
def get_conversations(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ConversationListItem]:
    """List recent conversations for the logged-in user (newest activity first)."""
    return list_conversations(db, current_user, limit=limit)


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationDetail:
    """Return all messages in a conversation, oldest first."""
    return get_conversation_detail(db, conversation_id, current_user)
