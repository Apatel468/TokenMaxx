"""
Chat router — multi-turn conversations with Groq routing (Phase 3A).

POST /chat accepts an optional conversation_id:
  - omit it  → start a new conversation
  - include it → load prior messages, send full context to the model
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import ChatRequest, ChatResponse
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
def chat(request: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    """
    Process a user prompt with optional conversation memory.

    1. Load prior messages if conversation_id is provided.
    2. Classify the latest prompt (task type).
    3. Build context including full message history.
    4. Route to the best Groq model.
    5. Call Groq with the full conversation context.
    6. Save user + assistant messages and routing metrics.
    """
    # Step 1: Load existing thread (if continuing a conversation)
    prior_messages: list[dict] = []
    if request.conversation_id is not None:
        get_conversation_or_404(db, request.conversation_id)
        prior_messages = load_message_history(db, request.conversation_id)

    # Step 2: Classify the latest user message
    analysis = analyze_prompt(request.prompt)

    # Step 3: Build context with prior turns for token estimate + model history
    context = build_context(request.prompt, analysis, prior_messages=prior_messages)

    # Step 4: Pick Groq model from config/models.yaml
    decision = route(context)

    # Step 5: Send full message history to Groq (or mock fallback)
    model_response = generate_response(
        decision.groq_model,
        context,
        messages=context.message_history,
    )

    # Step 6: Cost vs. premium baseline
    costs = estimate_costs(decision.model_id, context, model_response)
    log_request_metrics(decision.model_id, context.task_type, model_response, costs)

    # Step 7: Persist user message, assistant reply, and model_run
    conversation_id = save_chat_turn(
        db=db,
        prompt=request.prompt,
        response_text=model_response.text,
        task_type=context.task_type,
        decision=decision,
        model_response=model_response,
        costs=costs,
        conversation_id=request.conversation_id,
    )

    return ChatResponse(
        conversation_id=conversation_id,
        original_prompt=request.prompt,
        task_type=context.task_type,
        selected_model=decision.model_label,
        reason_selected=decision.reason,
        mock_response=model_response.text,
        estimated_actual_cost=costs.actual_cost,
        estimated_premium_cost=costs.premium_cost,
        estimated_savings_percentage=costs.savings_percentage,
    )
