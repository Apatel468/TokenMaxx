"""
Chat router — multi-turn conversations with Groq routing (Phase 4).

POST /chat pipeline:
  1. Load prior messages (optional conversation_id)
  2. Classify prompt (prompt_analyzer)
  3. Enhance prompt (prompt_enhancer via context_builder)
  4. Route to Groq model (router_engine)
  5. Generate response (model_clients + LiteLLM)
  6. Track costs and persist to SQLite
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import User, get_db
from models import ChatRequest, ChatResponse
from services.auth_dependencies import get_current_user
from services.model_settings import NoModelsEnabledError
from services.context_builder import build_context
from services.conversation_store import (
    get_conversation_or_404,
    load_message_history,
    save_chat_turn,
)
from services.cost_tracker import estimate_costs, log_request_metrics
from services.model_clients import generate_response
from services.prompt_analyzer import analyze_prompt
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
    # Step 1: Load existing thread (if continuing a conversation)
    prior_messages: list[dict] = []
    if request.conversation_id is not None:
        get_conversation_or_404(db, request.conversation_id, user=current_user)
        prior_messages = load_message_history(db, request.conversation_id)

    # Step 2: Classify the latest user message (Groq LLM, or keywords if unavailable)
    analysis = analyze_prompt(request.prompt)

    # Step 3: Enhance prompt + build context (prompt_enhancer runs inside build_context)
    context = build_context(request.prompt, analysis, prior_messages=prior_messages)

    # Step 4: Score all enabled Groq models and pick the best
    try:
        decision = route(context, db, current_user.id)
    except NoModelsEnabledError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Step 5: Send system prompt + enhanced history to Groq (or mock fallback)
    model_response = generate_response(
        decision.groq_model,
        context,
        messages=context.message_history,
    )

    # Step 6: Cost vs. premium baseline
    costs = estimate_costs(decision.model_id, context, model_response)
    log_request_metrics(decision.model_id, context.task_type, model_response, costs)

    # Step 7: Persist original user text + enhancement metadata + model_run
    conversation_id, title = save_chat_turn(
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
        system_prompt=context.system_prompt,
        enhancement_reason=context.enhancement_reason,
    )

    return ChatResponse(
        conversation_id=conversation_id,
        title=title or "",
        original_prompt=request.prompt,
        enhanced_prompt=context.enhanced_prompt,
        system_prompt=context.system_prompt,
        enhancement_reason=context.enhancement_reason,
        enhancement_method=context.enhancement_method,
        task_type=context.task_type,
        selected_model=decision.model_label,
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
    )
