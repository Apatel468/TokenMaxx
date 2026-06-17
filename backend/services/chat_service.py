"""
Shared chat pipeline helpers for POST /chat and POST /chat/stream.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from database import User
from models import ChatRequest, ChatResponse, ModelRecommendation, PromptAnalysisOut
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
from services.model_clients import ModelResponse
from services.prompt_analyzer import AnalysisResult, analyze_prompt
from services.prompt_intelligence import PromptAnalysis
from services.prompt_enhancer import format_enhanced_prompt_for_display
from services.recommendations import build_top_recommendations
from services.activity_log_service import record_activity
from services.rag_service import apply_rag_to_context, rag_metadata_dict, retrieve_for_chat
from services.router_engine import RoutingDecision, route
from services.context_builder import PromptContext


def prompt_analysis_to_out(
    analysis: PromptAnalysis | None,
) -> PromptAnalysisOut | None:
    """Convert internal PromptAnalysis to API model."""
    if analysis is None:
        return None
    return PromptAnalysisOut(
        original_prompt=analysis.original_prompt,
        task_type=analysis.task_type,
        complexity_score=analysis.complexity_score,
        complexity_level=analysis.complexity_level,
        persona=analysis.persona,
        output_format=analysis.output_format,
        enhancement_strategy=analysis.enhancement_strategy,
        enhanced_prompt=format_enhanced_prompt_for_display(analysis.enhanced_prompt),
    )


def prepare_chat_turn(
    db: Session,
    user: User,
    request: ChatRequest,
) -> tuple[AnalysisResult, PromptContext, RoutingDecision, float, list[dict]]:
    """Classify, enhance, and route — shared by sync and streaming chat."""
    prior_messages: list[dict] = []
    if request.conversation_id is not None:
        get_conversation_or_404(db, request.conversation_id, user=user)
        prior_messages = load_message_history(db, request.conversation_id)

    if request.enhance_prompt:
        record_activity(
            db,
            user_id=user.id,
            event_type="prompt_enhancement_started",
            message="Prompt enhancement started.",
            conversation_id=request.conversation_id,
            metadata={"enhance_prompt": True},
        )

    analysis = analyze_prompt(request.prompt)
    context = build_context(
        request.prompt,
        analysis,
        prior_messages=prior_messages,
        enhance_prompt_enabled=request.enhance_prompt,
    )

    if request.enhance_prompt:
        record_activity(
            db,
            user_id=user.id,
            event_type="prompt_enhancement_completed",
            message="Prompt enhancement completed.",
            conversation_id=request.conversation_id,
            metadata={
                "task_type": context.task_type,
                "enhancement_method": context.enhancement_method,
            },
        )

    record_activity(
        db,
        user_id=user.id,
        event_type="rag_search_started",
        message="RAG document search started.",
        conversation_id=request.conversation_id,
    )
    rag_result = retrieve_for_chat(user.id, request.prompt)
    context = apply_rag_to_context(context, rag_result)
    record_activity(
        db,
        user_id=user.id,
        event_type="rag_chunks_retrieved",
        message="RAG document search completed.",
        conversation_id=request.conversation_id,
        metadata={
            "rag_used": rag_result.rag_used,
            "chunk_count": rag_result.retrieved_chunk_count,
            "source_filenames": rag_result.source_filenames,
        },
    )

    enhancement_cost_saved = (
        0.0
        if request.enhance_prompt
        else estimate_enhancement_cost_saved(request.prompt)
    )

    record_activity(
        db,
        user_id=user.id,
        event_type="routing_started",
        message="Model routing started.",
        conversation_id=request.conversation_id,
        metadata={"task_type": context.task_type},
    )
    decision = route(context, db, user.id)
    record_activity(
        db,
        user_id=user.id,
        event_type="routing_completed",
        message="Model routing completed.",
        conversation_id=request.conversation_id,
        metadata={
            "task_type": context.task_type,
            "model": decision.model_id,
            "provider": "groq",
            "routing_score": decision.score,
        },
    )
    return analysis, context, decision, enhancement_cost_saved, prior_messages


def persist_chat_turn(
    db: Session,
    user: User,
    request: ChatRequest,
    analysis: AnalysisResult,
    context: PromptContext,
    decision: RoutingDecision,
    model_response: ModelResponse,
    enhancement_cost_saved: float,
) -> tuple[int, str, int, int, object]:
    """Save turn to SQLite and return ids."""
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
        user_id=user.id,
        conversation_id=request.conversation_id,
        enhanced_prompt=context.enhanced_prompt,
        system_prompt=context.system_prompt or "",
        enhancement_reason=context.enhancement_reason,
        enhancement_method=context.enhancement_method,
        enhancement_enabled=request.enhance_prompt,
        enhancement_cost_saved=enhancement_cost_saved,
        classification_method=analysis.classification_method,
        classification_reason=analysis.classification_reason,
        classification_confidence=analysis.confidence,
        prompt_analysis=context.prompt_analysis,
        rag_used=context.rag_used,
        rag_chunk_count=context.retrieved_chunk_count,
        rag_source_documents=context.source_documents,
        rag_source_filenames=context.source_filenames,
    )
    return conversation_id, title or "", user_message_id, assistant_message_id, costs


def build_routing_metadata(
    db: Session,
    user: User,
    request: ChatRequest,
    analysis: AnalysisResult,
    context: PromptContext,
    decision: RoutingDecision,
) -> dict:
    """Routing panel fields available before generation completes."""
    top_recs = build_top_recommendations(
        db,
        user.id,
        decision.candidate_models,
        context,
        limit=5,
    )
    return {
        "original_prompt": request.prompt,
        "enhanced_prompt": format_enhanced_prompt_for_display(context.enhanced_prompt),
        "system_prompt": context.system_prompt or "",
        "enhancement_reason": context.enhancement_reason,
        "enhancement_method": context.enhancement_method,
        "task_type": context.task_type,
        "classification_confidence": analysis.confidence,
        "classification_reason": analysis.classification_reason,
        "classification_method": analysis.classification_method,
        "selected_model": decision.model_label,
        "selected_model_id": decision.model_id,
        "reason_selected": decision.reason,
        "preferred_model": decision.preferred_model_id,
        "used_fallback": decision.used_fallback,
        "fallback_message": decision.fallback_message,
        "routing_score": decision.score,
        "candidate_models": decision.candidate_models,
        "top_candidate_scores": decision.candidate_models[:3],
        "top_recommendations": top_recs,
        "prompt_analysis": prompt_analysis_to_out(context.prompt_analysis),
        **rag_metadata_dict(context),
    }


def build_chat_response(
    request: ChatRequest,
    analysis: AnalysisResult,
    context: PromptContext,
    decision: RoutingDecision,
    model_response: ModelResponse,
    costs,
    conversation_id: int,
    title: str,
    user_message_id: int,
    assistant_message_id: int,
    db: Session,
    user: User,
) -> ChatResponse:
    """Assemble the full ChatResponse payload."""
    top_recs = build_top_recommendations(
        db,
        user.id,
        decision.candidate_models,
        context,
        limit=5,
    )
    return ChatResponse(
        conversation_id=conversation_id,
        title=title,
        original_prompt=request.prompt,
        enhanced_prompt=format_enhanced_prompt_for_display(context.enhanced_prompt),
        system_prompt=context.system_prompt or "",
        enhancement_reason=context.enhancement_reason,
        enhancement_method=context.enhancement_method,
        task_type=context.task_type,
        classification_confidence=analysis.confidence,
        classification_reason=analysis.classification_reason,
        classification_method=analysis.classification_method,
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
        top_candidate_scores=decision.candidate_models[:3],
        top_recommendations=[ModelRecommendation(**r) for r in top_recs],
        user_message_id=user_message_id,
        assistant_message_id=assistant_message_id,
        prompt_analysis=prompt_analysis_to_out(context.prompt_analysis),
        **rag_metadata_dict(context),
    )
