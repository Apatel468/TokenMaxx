"""
Conversation Store — read/write multi-turn conversations in SQLite (Phase 3A).
"""

import json
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from database import (
    Conversation,
    GeneratedDocument,
    GeneratedImage,
    Message,
    MessageSentiment,
    ModelRun,
    User,
)
from models import (
    ConversationDetail,
    ConversationListItem,
    GenerationArtifactOut,
    MessageOut,
    PromptAnalysisOut,
    SentimentOut,
    WebSourceOut,
)
from services.cost_tracker import CostEstimate
from services.model_clients import ModelResponse
from services.conversation_title import generate_conversation_title
from services.timezone_utils import format_timestamp_eastern
from services.router_engine import RoutingDecision
from services.prompt_enhancer import format_enhanced_prompt_for_display
from services.prompt_intelligence import PromptAnalysis
from services.rag_service import (
    deserialize_source_filenames,
    serialize_source_documents,
    serialize_source_filenames,
)
from services.web_research_service import (
    WebSource,
    deserialize_web_sources,
    serialize_web_sources,
)

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


def _prompt_analysis_for_assistant(
    db: Session, message: Message
) -> PromptAnalysisOut | None:
    """Load Prompt Intelligence v2 metadata for an assistant turn."""
    if message.role != "assistant":
        return None

    run = (
        db.query(ModelRun)
        .filter(ModelRun.assistant_message_id == message.id)
        .first()
    )
    if not run or run.prompt_complexity_level is None:
        return None

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
    return PromptAnalysisOut(
        original_prompt=original,
        task_type=run.prompt_enhancement_task_type or run.task_type or "general_qa",
        complexity_score=int(run.prompt_complexity_score or 0),
        complexity_level=run.prompt_complexity_level or "medium",
        persona=run.prompt_persona or "",
        output_format=run.prompt_output_format or "",
        enhancement_strategy=run.enhancement_strategy or "",
        enhanced_prompt=enhanced,
    )


def _rag_for_assistant(db: Session, message: Message) -> tuple[bool, list[str]]:
    """Return (rag_used, source_filenames) for an assistant turn."""
    if message.role != "assistant":
        return False, []

    run = (
        db.query(ModelRun)
        .filter(ModelRun.assistant_message_id == message.id)
        .first()
    )
    if not run or not run.rag_used:
        return False, []

    return True, deserialize_source_filenames(run.rag_source_filenames)


def _web_research_for_assistant(
    db: Session, message: Message
) -> tuple[bool, list[dict], str]:
    """Return (web_research_used, web_sources, search_query) for an assistant turn."""
    if message.role != "assistant":
        return False, [], ""

    run = (
        db.query(ModelRun)
        .filter(ModelRun.assistant_message_id == message.id)
        .first()
    )
    if not run or not run.web_research_used:
        return False, [], ""

    sources = deserialize_web_sources(run.web_sources_json)
    return True, sources, run.web_search_query or ""


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


def _artifact_for_message(db: Session, message: Message) -> GenerationArtifactOut | None:
    """Load generation artifact metadata for an assistant message."""
    if message.role != "assistant" or not message.generation_artifact_type:
        return None

    artifact_id = message.generation_artifact_id
    if not artifact_id:
        return None

    if message.generation_artifact_type == "document":
        row = db.query(GeneratedDocument).filter(GeneratedDocument.id == artifact_id).first()
        if not row:
            return None
        return GenerationArtifactOut(
            artifact_type="document",
            artifact_id=row.id,
            file_name=row.file_name,
            file_type=row.file_type,
            file_size=row.file_size,
            download_url=f"/generations/documents/{row.id}/download",
            preview_url=f"/generations/documents/{row.id}/preview",
            created_at=format_timestamp_eastern(row.created_at),
            model_used=row.model_used,
            file_count=row.file_count,
            is_archive=row.is_archive,
        )

    if message.generation_artifact_type == "image":
        row = db.query(GeneratedImage).filter(GeneratedImage.id == artifact_id).first()
        if not row:
            return None
        return GenerationArtifactOut(
            artifact_type="image",
            artifact_id=row.id,
            file_name=row.storage_path.split("/")[-1],
            file_type="png",
            file_size=0,
            download_url=f"/generations/images/{row.id}/download",
            preview_url=f"/generations/images/{row.id}/file",
            created_at=format_timestamp_eastern(row.created_at),
            provider_used=row.provider_used,
            model_used=row.model_used,
            image_type=row.image_type,
            width=row.width,
            height=row.height,
        )

    return None


def _sentiment_for_user_message(db: Session, message: Message) -> SentimentOut | None:
    """Load stored sentiment for a user message."""
    if message.role != "user":
        return None
    row = (
        db.query(MessageSentiment)
        .filter(MessageSentiment.message_id == message.id)
        .first()
    )
    if not row:
        return None
    return SentimentOut(
        label=row.label,
        confidence=round(row.confidence * 100, 1),
        explanation=row.explanation,
        method=row.method or "rules",
        message_id=row.message_id,
        conversation_id=row.conversation_id,
        created_at=format_timestamp_eastern(row.created_at),
    )


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
    prompt_analysis: PromptAnalysis | None = None,
    rag_used: bool = False,
    rag_chunk_count: int = 0,
    rag_source_documents: list[int] | None = None,
    rag_source_filenames: list[str] | None = None,
    web_research_used: bool = False,
    web_search_query: str = "",
    web_search_provider: str = "",
    web_sources: list[WebSource] | None = None,
    web_scrape_duration_ms: float = 0.0,
    content_type: str = "text",
    generation_artifact_type: str | None = None,
    generation_artifact_id: int | None = None,
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
        content_type=content_type,
        generation_artifact_type=generation_artifact_type,
        generation_artifact_id=generation_artifact_id,
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
        provider=decision.provider,
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
        prompt_complexity_score=(
            prompt_analysis.complexity_score if prompt_analysis else None
        ),
        prompt_complexity_level=(
            prompt_analysis.complexity_level if prompt_analysis else None
        ),
        prompt_persona=prompt_analysis.persona if prompt_analysis else None,
        prompt_output_format=prompt_analysis.output_format if prompt_analysis else None,
        prompt_enhancement_task_type=(
            prompt_analysis.task_type if prompt_analysis else None
        ),
        enhancement_strategy=(
            prompt_analysis.enhancement_strategy if prompt_analysis else None
        ),
        rag_used=rag_used,
        rag_chunk_count=rag_chunk_count or None,
        rag_source_documents=serialize_source_documents(rag_source_documents or []),
        rag_source_filenames=serialize_source_filenames(rag_source_filenames or []),
        web_research_used=web_research_used,
        web_search_query=web_search_query or None,
        web_search_provider=web_search_provider or None,
        web_source_urls=json.dumps([s.url for s in (web_sources or [])]) if web_sources else None,
        web_source_titles=serialize_source_filenames(
            [s.title for s in (web_sources or []) if s.title]
        ),
        web_sources_json=serialize_web_sources(web_sources or []),
        web_scrape_duration_ms=web_scrape_duration_ms or None,
        web_source_count=len(web_sources or []) or None,
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
        prompt_analysis = _prompt_analysis_for_assistant(db, m)
        rag_used, source_filenames = _rag_for_assistant(db, m)
        web_used, web_sources, web_query = _web_research_for_assistant(db, m)
        sentiment = _sentiment_for_user_message(db, m)
        message_rows.append(
            MessageOut(
                id=m.id,
                role=m.role,
                content=m.content,
                content_type=m.content_type or "text",
                response_label=m.response_label or "",
                selected_model=_selected_model_for_message(db, m),
                original_prompt=original_prompt,
                enhanced_prompt=enhanced_prompt,
                enhancement_method=enhancement_method,
                prompt_analysis=prompt_analysis,
                rag_used=rag_used,
                source_filenames=source_filenames,
                web_research_used=web_used,
                web_sources=[WebSourceOut(**src) for src in web_sources],
                web_search_query=web_query,
                generation_artifact=_artifact_for_message(db, m),
                created_at=format_timestamp_eastern(m.created_at),
                sentiment=sentiment,
            )
        )

    return ConversationDetail(
        id=conversation.id,
        title=title,
        messages=message_rows,
        created_at=format_timestamp_eastern(conversation.created_at),
        updated_at=format_timestamp_eastern(conversation.updated_at),
    )
