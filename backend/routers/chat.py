"""
Chat router — multi-turn conversations with Groq routing (Phase 4).

POST /chat pipeline:
  1. Load prior messages (optional conversation_id)
  2. Classify prompt (prompt_analyzer)
  3. Enhance prompt (prompt_enhancer via context_builder)
  4. Route to Groq model (router_engine)
  5. Generate response (model_clients + LiteLLM)
  6. Track costs and persist to SQLite

POST /chat/regenerate — user-selected model retry (no re-routing).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import User, get_db
from models import (
    ChatRequest,
    ChatResponse,
    ModelRecommendation,
    RegenerateRequest,
    RegenerateResponse,
)
from services.auth_dependencies import get_current_user
from services.model_settings import NoModelsEnabledError
from services.context_builder import build_context
from services.conversation_store import (
    get_conversation_or_404,
    load_message_history,
    save_chat_turn,
)
from services.cost_tracker import (
    estimate_costs,
    estimate_enhancement_cost_saved,
    log_request_metrics,
)
from services.model_clients import generate_response
from services.prompt_analyzer import analyze_prompt
from services.recommendations import build_top_recommendations
from services.regenerate_service import regenerate_with_model
from services.router_engine import route

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    """
    Process a user prompt with optional conversation memory.

    1. Load prior messages if conversation_id is provided.
    2. Classify the latest prompt (task type).
    3. Enhance prompt and build context (includes full message history).
    4. Route to the best Groq model.
    5. Call Groq with system prompt + enhanced conversation context.
    6. Save user + assistant messages and routing metrics.
    """
    prior_messages: list[dict] = []
    if request.conversation_id is not None:
        get_conversation_or_404(db, request.conversation_id, user=current_user)
        prior_messages = load_message_history(db, request.conversation_id)

    analysis = analyze_prompt(request.prompt)

    context = build_context(
        request.prompt,
        analysis,
        prior_messages=prior_messages,
        enhance_prompt_enabled=request.enhance_prompt,
    )
    enhancement_cost_saved = (
        0.0
        if request.enhance_prompt
        else estimate_enhancement_cost_saved(request.prompt)
    )

    try:
        decision = route(context, db, current_user.id)
    except NoModelsEnabledError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    model_response = generate_response(
        decision.groq_model,
        context,
        messages=context.message_history,
    )

    costs = estimate_costs(decision.model_id, context, model_response)
    log_request_metrics(decision.model_id, context.task_type, model_response, costs)

    conversation_id, title, user_message_id, assistant_message_id = save_chat_turn(
        db=db,
        prompt=request.prompt,
        response_text=model_response.text,
        task_type=context.task_type,
        decision=decision,
        model_response=model_response,
        costs=costs,
        user_id=current_user.id,
        conversation_id=request.conversation_id,
        enhanced_prompt=context.enhanced_prompt,
        system_prompt=context.system_prompt or "",
        enhancement_reason=context.enhancement_reason,
        enhancement_method=context.enhancement_method,
        enhancement_enabled=request.enhance_prompt,
        enhancement_cost_saved=enhancement_cost_saved,
    )

    top_recs = build_top_recommendations(
        db,
        current_user.id,
        decision.candidate_models,
        context,
        limit=5,
    )

    return ChatResponse(
        conversation_id=conversation_id,
        title=title or "",
        original_prompt=request.prompt,
        enhanced_prompt=context.enhanced_prompt,
        system_prompt=context.system_prompt or "",
        enhancement_reason=context.enhancement_reason,
        enhancement_method=context.enhancement_method,
        task_type=context.task_type,
        selected_model=decision.model_label,
        selected_model_id=decision.model_id,
        reason_selected=decision.reason,
        mock_response=model_response.text,
        estimated_actual_cost=costs.actual_cost,
        estimated_premium_cost=costs.premium_cost,
        estimated_savings_percentage=costs.savings_percentage,
        preferred_model=decision.preferred_model_id,
        used_fallback=decision.used_fallback,
        fallback_message=decision.fallback_message,
        routing_score=decision.score,
        candidate_models=decision.candidate_models,
        top_recommendations=[ModelRecommendation(**r) for r in top_recs],
        user_message_id=user_message_id,
        assistant_message_id=assistant_message_id,
    )


@router.post("/regenerate", response_model=RegenerateResponse)
def regenerate_chat(
    request: RegenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RegenerateResponse:
    """
    Regenerate the response for a turn using a user-selected model.

    Reuses stored prompts and context — does not re-classify or re-route.
    """
    result = regenerate_with_model(
        db=db,
        user=current_user,
        conversation_id=request.conversation_id,
        message_id=request.message_id,
        model_id=request.model_id,
    )
    return RegenerateResponse(**result)
