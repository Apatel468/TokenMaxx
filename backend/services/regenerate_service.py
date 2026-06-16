"""
Regenerate Service — re-run a turn with a user-selected model.

Skips classification, enhancement, and routing. Reuses stored prompts/context.
"""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from database import Message, ModelRun, User
from services.context_builder import PromptContext
from services.conversation_store import get_conversation_or_404
from services.cost_tracker import estimate_costs, log_request_metrics
from services.groq_models import get_model_record, get_routable_models
from services.model_clients import generate_response
from services.model_settings import get_model_disabled_reason

REGENERATE_LABEL = "User Selected Model"


def _load_turn_context(
    db: Session,
    conversation_id: int,
    user_message_id: int,
) -> tuple[Message, ModelRun, list[dict], PromptContext]:
    """Rebuild PromptContext from the original turn without re-enhancing."""
    user_msg = (
        db.query(Message)
        .filter(
            Message.id == user_message_id,
            Message.conversation_id == conversation_id,
            Message.role == "user",
        )
        .first()
    )
    if not user_msg:
        raise HTTPException(status_code=404, detail="User message not found.")

    first_run = (
        db.query(ModelRun)
        .filter(ModelRun.turn_user_message_id == user_message_id)
        .order_by(ModelRun.created_at.asc())
        .first()
    )
    if not first_run:
        assistant_after = (
            db.query(Message)
            .filter(
                Message.conversation_id == conversation_id,
                Message.role == "assistant",
                Message.created_at > user_msg.created_at,
            )
            .order_by(Message.created_at.asc())
            .first()
        )
        if assistant_after:
            first_run = (
                db.query(ModelRun)
                .filter(ModelRun.assistant_message_id == assistant_after.id)
                .first()
            )
    if not first_run:
        raise HTTPException(
            status_code=404,
            detail="No routing data found for this message. Send a new chat first.",
        )

    prior_rows = (
        db.query(Message)
        .filter(
            Message.conversation_id == conversation_id,
            Message.created_at < user_msg.created_at,
        )
        .order_by(Message.created_at.asc())
        .all()
    )
    prior = [{"role": m.role, "content": m.content} for m in prior_rows]
    enhanced = first_run.enhanced_prompt or user_msg.content
    full_history = prior + [{"role": "user", "content": enhanced}]

    context = PromptContext(
        prompt=user_msg.content,
        task_type=first_run.task_type,
        confidence=1.0,
        estimated_input_tokens=max(
            sum(len(m["content"]) for m in full_history) // 4, 1
        ),
        is_long_prompt=False,
        keywords_matched=[],
        enhanced_prompt=enhanced,
        system_prompt=first_run.system_prompt,
        enhancement_reason=first_run.enhancement_reason or "",
        enhancement_method="reused",
        message_history=full_history,
    )
    return user_msg, first_run, prior, context


def regenerate_with_model(
    db: Session,
    user: User,
    conversation_id: int,
    message_id: int,
    model_id: str,
) -> dict:
    """Generate a new assistant reply with the chosen model; persist to DB."""
    get_conversation_or_404(db, conversation_id, user=user)

    catalog_ids = {r.model_id for r in get_routable_models()}
    if model_id not in catalog_ids:
        raise HTTPException(status_code=400, detail=f"Unknown model: {model_id}")

    disabled = get_model_disabled_reason(db, user.id, model_id)
    if disabled:
        raise HTTPException(status_code=400, detail=disabled)

    _user_msg, first_run, _prior, context = _load_turn_context(
        db, conversation_id, message_id
    )

    model_response = generate_response(
        model_id,
        context,
        messages=context.message_history,
    )
    costs = estimate_costs(model_id, context, model_response)
    log_request_metrics(model_id, context.task_type, model_response, costs)

    assistant_message = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=model_response.text,
        response_label=REGENERATE_LABEL,
    )
    db.add(assistant_message)
    db.flush()

    savings_usd = costs.premium_cost - costs.actual_cost
    model_run = ModelRun(
        conversation_id=conversation_id,
        user_id=user.id,
        assistant_message_id=assistant_message.id,
        task_type=context.task_type,
        selected_model=model_id,
        reason_selected=f"User-selected regeneration from {first_run.selected_model}",
        input_tokens=costs.input_tokens,
        output_tokens=costs.output_tokens,
        estimated_cost=costs.actual_cost,
        premium_model_cost=costs.premium_cost,
        savings_usd=round(savings_usd, 6),
        savings_percentage=costs.savings_percentage,
        latency_ms=model_response.latency_ms,
        is_mock=model_response.is_mock,
        enhanced_prompt=context.enhanced_prompt,
        system_prompt=context.system_prompt,
        enhancement_reason=context.enhancement_reason,
        enhancement_method="reused",
        enhancement_enabled=bool(first_run.enhancement_enabled),
        enhancement_cost_saved=0.0,
        is_regeneration=True,
        original_model=first_run.selected_model,
        regenerated_model=model_id,
        turn_user_message_id=message_id,
    )
    db.add(model_run)
    db.commit()
    db.refresh(assistant_message)

    record = get_model_record(model_id)
    model_label = record.model_name if record else model_id
    provider = record.provider if record else "groq"
    regeneration_reason = (
        f"User manually regenerated this response with {model_label}."
    )

    return {
        "response": model_response.text,
        "model_used": model_id,
        "model_label": model_label,
        "provider": provider,
        "task_type": context.task_type,
        "regeneration_reason": regeneration_reason,
        "actual_cost": costs.actual_cost,
        "premium_cost": costs.premium_cost,
        "savings_percentage": costs.savings_percentage,
        "input_tokens": costs.input_tokens,
        "output_tokens": costs.output_tokens,
        "latency_ms": model_response.latency_ms,
        "assistant_message_id": assistant_message.id,
        "response_label": REGENERATE_LABEL,
        "was_user_selected": True,
    }
