"""
Conversation Store — read/write multi-turn conversations in SQLite (Phase 3A).

Each conversation can have many user + assistant messages.
Every assistant reply also gets a model_runs row with routing + cost data.
"""

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from database import Conversation, Message, ModelRun
from models import ConversationDetail, ConversationListItem, MessageOut
from services.cost_tracker import CostEstimate
from services.model_clients import ModelResponse
from services.conversation_title import generate_conversation_title
from services.router_engine import RoutingDecision


def get_conversation_or_404(db: Session, conversation_id: int) -> Conversation:
    """Load a conversation by id or raise 404."""
    conversation = (
        db.query(Conversation).filter(Conversation.id == conversation_id).first()
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


def _first_exchange_messages(
    db: Session, conversation_id: int
) -> tuple[str | None, str | None]:
    """Return (first user content, first assistant content) for a conversation."""
    rows = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .all()
    )
    first_user = next((m for m in rows if m.role == "user"), None)
    first_assistant = next((m for m in rows if m.role == "assistant"), None)
    user_content = first_user.content if first_user else None
    assistant_content = first_assistant.content if first_assistant else None
    return user_content, assistant_content


def _generate_title_from_first_exchange(
    db: Session,
    conversation: Conversation,
    *,
    use_ai: bool = True,
) -> str | None:
    """Build a title from the first user + assistant messages, if available."""
    if conversation.title and conversation.title.strip():
        return conversation.title.strip()

    user_content, assistant_content = _first_exchange_messages(db, conversation.id)
    if not user_content or not assistant_content:
        return None

    return generate_conversation_title(
        user_content, assistant_content, use_ai=use_ai
    )


def _maybe_generate_and_store_title(
    db: Session,
    conversation: Conversation,
    *,
    use_ai: bool = True,
) -> str | None:
    """
    Generate and persist a title when missing and the first reply exists.

    Never overwrites an existing title.
    """
    if conversation.title and conversation.title.strip():
        return conversation.title.strip()

    title = _generate_title_from_first_exchange(db, conversation, use_ai=use_ai)
    if not title:
        return None

    conversation.title = title
    db.commit()
    db.refresh(conversation)
    return title


def _resolve_title(
    db: Session,
    conversation: Conversation,
    *,
    persist_if_missing: bool = False,
    use_ai: bool = True,
) -> str:
    """
    Return stored title, or a placeholder until the first reply is saved.

    When persist_if_missing is True, backfills a missing title if the first
    user + assistant messages are already in the database.
    """
    if conversation.title and conversation.title.strip():
        return conversation.title.strip()

    if persist_if_missing:
        generated = _maybe_generate_and_store_title(
            db, conversation, use_ai=use_ai
        )
        if generated:
            return generated

    return "New Chat"


def load_message_history(db: Session, conversation_id: int) -> list[dict]:
    """
    Load prior messages as LiteLLM-style dicts: {role, content}.

    Ordered oldest → newest. Used to build context for follow-up messages.
    """
    rows = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .all()
    )
    return [{"role": row.role, "content": row.content} for row in rows]


def save_chat_turn(
    db: Session,
    prompt: str,
    response_text: str,
    task_type: str,
    decision: RoutingDecision,
    model_response: ModelResponse,
    costs: CostEstimate,
    conversation_id: int | None = None,
    enhanced_prompt: str = "",
    system_prompt: str = "",
    enhancement_reason: str = "",
) -> tuple[int, str | None]:
    """
    Save one user message + assistant reply (+ model_run).

    If conversation_id is None, starts a new conversation.
    If conversation_id is set, appends to that existing thread.

    After the first assistant reply, generates and stores a title once.

    Returns:
        (conversation id, title or None if not yet generated)
    """
    if conversation_id:
        conversation = get_conversation_or_404(db, conversation_id)
        conversation.updated_at = datetime.now(timezone.utc)
    else:
        conversation = Conversation()
        db.add(conversation)
        db.flush()

    # User turn
    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=prompt,
    )
    db.add(user_message)

    # Assistant turn
    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=response_text,
    )
    db.add(assistant_message)
    db.flush()

    savings_usd = costs.premium_cost - costs.actual_cost
    model_run = ModelRun(
        conversation_id=conversation.id,
        assistant_message_id=assistant_message.id,
        task_type=task_type,
        selected_model=decision.model_id,
        reason_selected=decision.reason,
        input_tokens=costs.input_tokens,
        output_tokens=costs.output_tokens,
        estimated_cost=costs.actual_cost,
        premium_model_cost=costs.premium_cost,
        savings_usd=round(savings_usd, 6),
        savings_percentage=costs.savings_percentage,
        latency_ms=model_response.latency_ms,
        is_mock=model_response.is_mock,
        enhanced_prompt=enhanced_prompt,
        system_prompt=system_prompt,
        enhancement_reason=enhancement_reason,
    )
    db.add(model_run)

    # Generate title in the same commit as the first assistant reply
    title: str | None = None
    if not (conversation.title and conversation.title.strip()):
        title = _generate_title_from_first_exchange(db, conversation)
        if title:
            conversation.title = title

    db.commit()
    db.refresh(conversation)

    return conversation.id, conversation.title or title


def list_conversations(db: Session, limit: int = 50) -> list[ConversationListItem]:
    """Return recent conversations for GET /conversations."""
    rows = (
        db.query(Conversation)
        .order_by(Conversation.updated_at.desc())
        .limit(limit)
        .all()
    )

    results: list[ConversationListItem] = []
    for conv in rows:
        messages = (
            db.query(Message)
            .filter(Message.conversation_id == conv.id)
            .order_by(Message.created_at.asc())
            .all()
        )
        # Fast rule-based backfill for old threads; new chats get AI titles on save
        title = _resolve_title(
            db, conv, persist_if_missing=True, use_ai=False
        )
        preview = title

        results.append(
            ConversationListItem(
                id=conv.id,
                title=title,
                preview=preview,
                message_count=len(messages),
                created_at=conv.created_at,
                updated_at=conv.updated_at,
            )
        )

    return results


def get_conversation_detail(db: Session, conversation_id: int) -> ConversationDetail:
    """Return full message history for GET /conversations/{id}."""
    conversation = get_conversation_or_404(db, conversation_id)
    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .all()
    )

    title = _resolve_title(db, conversation, persist_if_missing=True)

    return ConversationDetail(
        id=conversation.id,
        title=title,
        messages=[
            MessageOut(
                id=m.id,
                role=m.role,
                content=m.content,
                created_at=m.created_at,
            )
            for m in messages
        ],
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )
