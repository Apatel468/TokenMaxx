"""
Chat router — multi-turn conversations with Groq routing (Phase 4).

POST /chat pipeline:
  1. Load prior messages (optional conversation_id)
  2. Classify prompt (prompt_analyzer)
  3. Enhance prompt (prompt_enhancer via context_builder)
  4. Route to Groq model (router_engine)
  5. Generate response (model_clients + LiteLLM)
  6. Track costs and persist to SQLite

POST /chat/stream — same pipeline with SSE token streaming.
POST /chat/regenerate — user-selected model retry (no re-routing).
"""

import json
import logging
import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import User, get_db
from models import (
    ChatRequest,
    ChatResponse,
    RegenerateRequest,
    RegenerateResponse,
)
from services.auth_dependencies import get_current_user
from services.chat_service import (
    build_chat_response,
    build_routing_metadata,
    persist_chat_turn,
    prepare_chat_turn,
)
from services.activity_log_service import record_activity
from services.model_clients import (
    MissingApiKeyError,
    _has_groq_key,
    _has_provider_key,
    build_response_from_stream,
    generate_response,
    stream_response,
)
from services.model_settings import NoModelsEnabledError
from services.regenerate_service import regenerate_with_model
from services.sse import format_sse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

_STREAM_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


@router.post("", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    """
    Process a user prompt with optional conversation memory (non-streaming).

    1. Load prior messages if conversation_id is provided.
    2. Classify the latest prompt (task type).
    3. Enhance prompt and build context (includes full message history).
    4. Route to the best Groq model.
    5. Call Groq with system prompt + enhanced conversation context.
    6. Save user + assistant messages and routing metrics.
    """
    try:
        record_activity(
            db,
            user_id=current_user.id,
            event_type="chat_request_received",
            message="Chat request received.",
            conversation_id=request.conversation_id,
            metadata={"enhance_prompt": request.enhance_prompt},
        )
        analysis, context, decision, enhancement_cost_saved, _prior = prepare_chat_turn(
            db, current_user, request
        )
    except NoModelsEnabledError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    record_activity(
        db,
        user_id=current_user.id,
        event_type="model_call_started",
        message="Model call started.",
        conversation_id=request.conversation_id,
        metadata={"model": decision.model_id, "provider": "groq", "task_type": context.task_type},
    )
    try:
        model_response = generate_response(
            decision.groq_model,
            context,
            messages=context.message_history,
            db=db,
            user_id=current_user.id,
        )
    except MissingApiKeyError as exc:
        record_activity(
            db,
            user_id=current_user.id,
            level="error",
            event_type="model_call_failed",
            message=str(exc),
            conversation_id=request.conversation_id,
            metadata={"provider": exc.provider},
        )
        db.commit()
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        record_activity(
            db,
            user_id=current_user.id,
            level="error",
            event_type="model_call_failed",
            message="Model call failed.",
            conversation_id=request.conversation_id,
            metadata={"model": decision.model_id, "error": str(exc)},
        )
        db.commit()
        raise

    record_activity(
        db,
        user_id=current_user.id,
        event_type="model_call_completed",
        message="Model call completed.",
        conversation_id=request.conversation_id,
        metadata={
            "model": decision.model_id,
            "provider": "groq",
            "latency_ms": model_response.latency_ms,
            "input_tokens": model_response.input_tokens,
            "output_tokens": model_response.estimated_output_tokens,
        },
    )

    conversation_id, title, user_message_id, assistant_message_id, costs = persist_chat_turn(
        db,
        current_user,
        request,
        analysis,
        context,
        decision,
        model_response,
        enhancement_cost_saved,
    )
    db.commit()

    return build_chat_response(
        request,
        analysis,
        context,
        decision,
        model_response,
        costs,
        conversation_id,
        title,
        user_message_id,
        assistant_message_id,
        db,
        current_user,
    )


@router.post("/stream")
def chat_stream(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """
    Stream a chat response as Server-Sent Events.

    Events: routing_start, routing_complete, token, complete, error
    """

    def event_generator():
        yield format_sse("routing_start", {})

        try:
            record_activity(
                db,
                user_id=current_user.id,
                event_type="chat_request_received",
                message="Chat stream request received.",
                conversation_id=request.conversation_id,
                metadata={"enhance_prompt": request.enhance_prompt, "streaming": True},
            )
            analysis, context, decision, enhancement_cost_saved, _prior = (
                prepare_chat_turn(db, current_user, request)
            )
        except NoModelsEnabledError as exc:
            yield format_sse("error", {"message": str(exc)})
            return
        except Exception as exc:
            logger.exception("Chat stream preparation failed")
            yield format_sse("error", {"message": str(exc)})
            return

        routing_metadata = build_routing_metadata(
            db, current_user, request, analysis, context, decision
        )
        yield format_sse("routing_complete", routing_metadata)

        accumulated = ""
        start = time.perf_counter()
        record_activity(
            db,
            user_id=current_user.id,
            event_type="model_call_started",
            message="Streaming model call started.",
            conversation_id=request.conversation_id,
            metadata={"model": decision.model_id, "provider": "groq", "streaming": True},
        )
        try:
            for chunk in stream_response(
                decision.groq_model,
                context,
                messages=context.message_history,
                db=db,
                user_id=current_user.id,
            ):
                accumulated += chunk
                yield format_sse("token", {"content": chunk})
        except MissingApiKeyError as exc:
            record_activity(
                db,
                user_id=current_user.id,
                level="error",
                event_type="model_call_failed",
                message=str(exc),
                conversation_id=request.conversation_id,
                metadata={"provider": exc.provider, "streaming": True},
            )
            db.commit()
            yield format_sse("error", {"message": str(exc)})
            return
        except Exception as exc:
            logger.exception("Chat stream generation failed")
            record_activity(
                db,
                user_id=current_user.id,
                level="error",
                event_type="model_call_failed",
                message="Streaming model call failed.",
                conversation_id=request.conversation_id,
                metadata={"model": decision.model_id, "error": str(exc)},
            )
            db.commit()
            yield format_sse("error", {"message": str(exc)})
            return

        latency_ms = (time.perf_counter() - start) * 1000
        model_response = build_response_from_stream(
            decision.groq_model,
            context,
            accumulated,
            latency_ms=latency_ms,
            is_mock=not _has_provider_key(db, current_user.id, "groq"),
        )

        record_activity(
            db,
            user_id=current_user.id,
            event_type="model_call_completed",
            message="Streaming model call completed.",
            conversation_id=request.conversation_id,
            metadata={
                "model": decision.model_id,
                "provider": "groq",
                "latency_ms": latency_ms,
                "streaming": True,
            },
        )

        try:
            conversation_id, title, user_message_id, assistant_message_id, costs = (
                persist_chat_turn(
                    db,
                    current_user,
                    request,
                    analysis,
                    context,
                    decision,
                    model_response,
                    enhancement_cost_saved,
                )
            )
            response = build_chat_response(
                request,
                analysis,
                context,
                decision,
                model_response,
                costs,
                conversation_id,
                title,
                user_message_id,
                assistant_message_id,
                db,
                current_user,
            )
            db.commit()
            yield format_sse("complete", json.loads(response.model_dump_json()))
        except Exception as exc:
            logger.exception("Chat stream persistence failed")
            yield format_sse("error", {"message": str(exc)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=_STREAM_HEADERS,
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
