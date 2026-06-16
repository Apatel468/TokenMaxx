"""
Conversation Store — read/write multi-turn conversations in SQLite (Phase 3A).

Each conversation belongs to one user (user_id). Admins can access all threads
via separate admin endpoints; regular users only see their own rows.
"""

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from database import Conversation, Message, ModelRun, User
from models import ConversationDetail, ConversationListItem, MessageOut
from services.cost_tracker import CostEstimate
from services.model_clients import ModelResponse
from services.conversation_title import generate_conversation_title
from services.timezone_utils import format_timestamp_eastern
from services.router_engine import RoutingDecision
from services.prompt_enhancer import format_enhanced_prompt_for_display

ROUTER_LABEL = "Router Selected"
REGENERATE_LABEL = "User Selected Model"


def _selected_model_for_message(db: Session, message: Message) -> str:
    """Model id for a regenerated assistant message, linked via model_runs."""
    if message.role != "assistant" or message.response_label != REGENERATE_LABEL:
        return ""
    run = (
        db.query(ModelRun)
        .filter(ModelRun.assistant_message_id == message.id)
        .first()
    )
    if not run:
        return ""
    return run.regenerated_model or run.selected_model or ""


def _prompt_enhancement_for_assistant(
    db: Session, message: Message
) -> tuple[str, str, str]:
    """
    Return (original_prompt, enhanced_prompt, enhancement_method) for an assistant turn.

    Original text lives on the paired user message; enhanced text on model_runs.
    """
    if message.role != "assistant":
        return "", "", ""

    run = (
        db.query(ModelRun)
        .filter(ModelRun.assistant_message_id == message.id)
        .first()
    )
    if not run:
        return "", "", ""

    original = ""
    if run.turn_user_message_id:
        user_msg = (
            db.query(Message)
            .filter(Message.id == run.turn_user_message_id)
            .first()
        )
        if user_msg:
            original = user_msg.content

    if not original:
        prior_user = (
            db.query(Message)
            .filter(
                Message.conversation_id == message.conversation_id,
                Message.role == "user",
                Message.created_at < message.created_at,
            )
            .order_by(Message.created_at.desc())
            .first()
        )
        if prior_user:
            original = prior_user.content

    enhanced = format_enhanced_prompt_for_display(run.enhanced_prompt or "") or original
    method = run.enhancement_method or ""
    return original, enhanced, method


def _user_owns_conversation(conversation: Conversation, user: User) -> bool:
    """True when this user may read/write the conversation (admins use /admin for org-wide data)."""
    return conversation.user_id == user.id


def get_conversation_or_404(
    db: Session,
    conversation_id: int,
    user: User | None = None,
) -> Conversation:
    """Load a conversation by id; optionally enforce owner (403 if not allowed)."""
    conversation = (
        db.query(Conversation).filter(Conversation.id == conversation_id).first()
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if user is not None and not _user_owns_conversation(conversation, user):
        raise HTTPException(status_code=403, detail="Not your conversation.")
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
    """Load prior messages as LiteLLM-style dicts: {role, content}."""
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
    user_id: int,
    conversation_id: int | None = None,
    enhanced_prompt: str = "",
    system_prompt: str = "",
    enhancement_reason: str = "",
    enhancement_method: str = "",
    enhancement_enabled: bool = True,
    enhancement_cost_saved: float = 0.0,
    classification_method: str = "",
    classification_reason: str = "",
    classification_confidence: float = 0.0,
) -> tuple[int, str | None, int, int]:
    """Save one user message + assistant reply (+ model_run). Returns ids."""
    if conversation_id:
        conversation = get_conversation_or_404(db, conversation_id)
        if conversation.user_id is not None and conversation.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not your conversation.")
        if conversation.user_id is None:
            conversation.user_id = user_id
        conversation.updated_at = datetime.now(timezone.utc)
    else:
        conversation = Conversation(user_id=user_id)
        db.add(conversation)
        db.flush()

    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=prompt,
    )
    db.add(user_message)

    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=response_text,
        response_label=ROUTER_LABEL,
    )
    db.add(assistant_message)
    db.flush()

    savings_usd = costs.premium_cost - costs.actual_cost
    model_run = ModelRun(
        conversation_id=conversation.id,
        user_id=user_id,
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
        enhancement_method=enhancement_method,
        enhancement_enabled=enhancement_enabled,
        enhancement_cost_saved=round(enhancement_cost_saved, 6),
        turn_user_message_id=user_message.id,
        classification_method=classification_method or None,
        classification_reason=classification_reason or None,
        classification_confidence=classification_confidence or None,
    )
    db.add(model_run)

    title: str | None = None
    if not (conversation.title and conversation.title.strip()):
        title = _generate_title_from_first_exchange(db, conversation)
        if title:
            conversation.title = title

    db.commit()
    db.refresh(conversation)

    return conversation.id, conversation.title or title, user_message.id, assistant_message.id


def list_conversations(
    db: Session, user: User, limit: int = 50
) -> list[ConversationListItem]:
    """Return recent conversations for the current user only."""
    rows = (
        db.query(Conversation)
        .filter(Conversation.user_id == user.id)
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
        title = _resolve_title(db, conv, persist_if_missing=True, use_ai=False)

        results.append(
            ConversationListItem(
                id=conv.id,
                title=title,
                preview=title,
                message_count=len(messages),
                created_at=format_timestamp_eastern(conv.created_at),
                updated_at=format_timestamp_eastern(conv.updated_at),
            )
        )

    return results


def get_conversation_detail(
    db: Session, conversation_id: int, user: User
) -> ConversationDetail:
    """Return full message history if the user owns this conversation."""
    conversation = get_conversation_or_404(db, conversation_id, user=user)
    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .all()
    )

    title = _resolve_title(db, conversation, persist_if_missing=True)

    message_rows: list[MessageOut] = []
    for m in messages:
        original_prompt, enhanced_prompt, enhancement_method = (
            _prompt_enhancement_for_assistant(db, m)
        )
        message_rows.append(
            MessageOut(
                id=m.id,
                role=m.role,
                content=m.content,
                response_label=m.response_label or "",
                selected_model=_selected_model_for_message(db, m),
                original_prompt=original_prompt,
                enhanced_prompt=enhanced_prompt,
                enhancement_method=enhancement_method,
                created_at=format_timestamp_eastern(m.created_at),
            )
        )

    return ConversationDetail(
        id=conversation.id,
        title=title,
        messages=message_rows,
        created_at=format_timestamp_eastern(conversation.created_at),
        updated_at=format_timestamp_eastern(conversation.updated_at),
    )
