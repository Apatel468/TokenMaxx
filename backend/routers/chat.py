"""
Chat router — multi-turn conversations with routing and generation (Phase 4+).

POST /chat pipeline:
  1. Load prior messages (optional conversation_id)
  2. Classify prompt + detect generation intent
  3. Enhance prompt (prompt_enhancer via context_builder)
  4. Route to best model (router_engine)
  5. Generate: chat text | document file | image
  6. Track costs and persist to SQLite

POST /chat/stream — same pipeline with SSE (tokens for chat, progress for generation).
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
from services.activity_logger import new_request_id, record_activity, with_request_meta
from services.generation_service import run_document_generation, run_image_generation
from services.model_clients import (
    MissingApiKeyError,
    has_provider_key,
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


def _handle_document_sync(
    db, current_user, request, analysis, context, decision,
    generation_intent, enhancement_cost_saved, request_id,
) -> ChatResponse:
    record_activity(
        db,
        user_id=current_user.id,
        event_type="document_generation_started",
        message="Document generation started.",
        conversation_id=request.conversation_id,
        metadata=with_request_meta(
            request_id=request_id,
            file_type=generation_intent.file_type,
        ),
    )
    try:
        doc_result, doc_row, conv_id, title, user_msg_id, asst_msg_id, costs = (
            run_document_generation(
                db,
                current_user,
                request.prompt,
                context,
                analysis,
                decision,
                generation_intent,
                conversation_id=request.conversation_id,
                enhancement_cost_saved=enhancement_cost_saved,
                enhance_prompt=request.enhance_prompt,
            )
        )
    except Exception as exc:
        record_activity(
            db,
            user_id=current_user.id,
            level="error",
            event_type="generation_failed",
            message=str(exc),
            conversation_id=request.conversation_id,
            metadata=with_request_meta(request_id=request_id, modality="document"),
        )
        db.commit()
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    record_activity(
        db,
        user_id=current_user.id,
        event_type="document_generation_completed",
        message="Document generation completed.",
        conversation_id=conv_id,
        metadata=with_request_meta(
            request_id=request_id,
            document_id=doc_row.id,
            file_name=doc_row.file_name,
            latency_ms=doc_result.latency_ms,
        ),
    )
    db.commit()
    return build_chat_response(
        request,
        analysis,
        context,
        decision,
        doc_result.model_response,
        costs,
        conv_id,
        title,
        user_msg_id,
        asst_msg_id,
        db,
        current_user,
        modality="document",
        generation_artifact_id=doc_row.id,
    )


def _handle_image_sync(
    db, current_user, request, analysis, context, decision,
    generation_intent, enhancement_cost_saved, request_id,
) -> ChatResponse:
    record_activity(
        db,
        user_id=current_user.id,
        event_type="image_generation_started",
        message="Image generation started.",
        conversation_id=request.conversation_id,
        metadata=with_request_meta(
            request_id=request_id,
            image_type=generation_intent.image_type,
        ),
    )
    try:
        img_result, img_row, conv_id, title, user_msg_id, asst_msg_id = (
            run_image_generation(
                db,
                current_user,
                request.prompt,
                context,
                analysis,
                decision,
                generation_intent,
                conversation_id=request.conversation_id,
                enhancement_cost_saved=enhancement_cost_saved,
                enhance_prompt=request.enhance_prompt,
            )
        )
    except Exception as exc:
        record_activity(
            db,
            user_id=current_user.id,
            level="error",
            event_type="generation_failed",
            message=str(exc),
            conversation_id=request.conversation_id,
            metadata=with_request_meta(request_id=request_id, modality="image"),
        )
        db.commit()
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    from services.cost_tracker import CostEstimate
    from services.model_clients import ModelResponse

    model_response = ModelResponse(
        text=f"Generated image ({img_result.image_type})",
        estimated_output_tokens=0,
        is_mock=img_result.is_mock,
        latency_ms=img_result.latency_ms,
        provider=img_result.provider_used,
        litellm_model=img_result.model_used,
    )
    costs = CostEstimate(
        actual_cost=0.04 if not img_result.is_mock else 0.0,
        premium_cost=0.08,
        savings_percentage=50.0 if not img_result.is_mock else 100.0,
        input_tokens=0,
        output_tokens=0,
    )

    record_activity(
        db,
        user_id=current_user.id,
        event_type="image_generation_completed",
        message="Image generation completed.",
        conversation_id=conv_id,
        metadata=with_request_meta(
            request_id=request_id,
            image_id=img_row.id,
            latency_ms=img_result.latency_ms,
            provider=img_result.provider_used,
        ),
    )
    db.commit()
    return build_chat_response(
        request,
        analysis,
        context,
        decision,
        model_response,
        costs,
        conv_id,
        title,
        user_msg_id,
        asst_msg_id,
        db,
        current_user,
        modality="image",
        generation_artifact_id=img_row.id,
    )


@router.post("", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    """Process a user prompt — routes to chat, document, or image generation."""
    request_id = new_request_id()
    prompt_preview = request.prompt.strip()[:120]
    try:
        record_activity(
            db,
            user_id=current_user.id,
            event_type="chat_request_received",
            message="Chat request received.",
            conversation_id=request.conversation_id,
            metadata=with_request_meta(
                request_id=request_id,
                enhance_prompt=request.enhance_prompt,
                prompt_preview=prompt_preview,
            ),
        )
        analysis, context, decision, enhancement_cost_saved, _prior, generation_intent = (
            prepare_chat_turn(db, current_user, request, request_id=request_id)
        )
    except NoModelsEnabledError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if generation_intent.modality == "document":
        return _handle_document_sync(
            db, current_user, request, analysis, context, decision,
            generation_intent, enhancement_cost_saved, request_id,
        )

    if generation_intent.modality == "image":
        return _handle_image_sync(
            db, current_user, request, analysis, context, decision,
            generation_intent, enhancement_cost_saved, request_id,
        )

    record_activity(
        db,
        user_id=current_user.id,
        event_type="model_call_started",
        message="Model call started.",
        conversation_id=request.conversation_id,
        metadata=with_request_meta(
            request_id=request_id,
            model=decision.model_id,
            provider=decision.provider,
            task_type=context.task_type,
        ),
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
            metadata=with_request_meta(request_id=request_id, provider=exc.provider),
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
            metadata=with_request_meta(
                request_id=request_id,
                model=decision.model_id,
                error=str(exc),
            ),
        )
        db.commit()
        raise

    record_activity(
        db,
        user_id=current_user.id,
        event_type="model_call_completed",
        message="Model call completed.",
        conversation_id=request.conversation_id,
        metadata=with_request_meta(
            request_id=request_id,
            model=decision.model_id,
            provider=decision.provider,
            latency_ms=model_response.latency_ms,
            input_tokens=model_response.input_tokens,
            output_tokens=model_response.estimated_output_tokens,
        ),
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
        modality="chat",
    )


@router.post("/stream")
def chat_stream(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """
    Stream a chat response as Server-Sent Events.

    Events: routing_start, routing_complete, generation_start, generation_progress,
    artifact, token, complete, error
    """

    def event_generator():
        yield format_sse("routing_start", {})
        request_id = new_request_id()
        prompt_preview = request.prompt.strip()[:120]

        try:
            record_activity(
                db,
                user_id=current_user.id,
                event_type="chat_request_received",
                message="Chat stream request received.",
                conversation_id=request.conversation_id,
                metadata=with_request_meta(
                    request_id=request_id,
                    enhance_prompt=request.enhance_prompt,
                    streaming=True,
                    prompt_preview=prompt_preview,
                ),
            )
            analysis, context, decision, enhancement_cost_saved, _prior, generation_intent = (
                prepare_chat_turn(db, current_user, request, request_id=request_id)
            )
        except NoModelsEnabledError as exc:
            yield format_sse("error", {"message": str(exc)})
            return
        except Exception as exc:
            logger.exception("Chat stream preparation failed")
            yield format_sse("error", {"message": str(exc)})
            return

        routing_metadata = build_routing_metadata(
            db, current_user, request, analysis, context, decision, generation_intent
        )
        yield format_sse("routing_complete", routing_metadata)

        # Document or image generation — non-token stream
        if generation_intent.modality in ("document", "image"):
            yield format_sse(
                "generation_start",
                {
                    "modality": generation_intent.modality,
                    "file_type": generation_intent.file_type,
                    "image_type": generation_intent.image_type,
                },
            )
            yield format_sse(
                "generation_progress",
                {"status": "generating", "message": "Creating your file…"},
            )
            try:
                if generation_intent.modality == "document":
                    response = _handle_document_sync(
                        db, current_user, request, analysis, context, decision,
                        generation_intent, enhancement_cost_saved, request_id,
                    )
                else:
                    response = _handle_image_sync(
                        db, current_user, request, analysis, context, decision,
                        generation_intent, enhancement_cost_saved, request_id,
                    )
                payload = json.loads(response.model_dump_json())
                if response.generation_artifact:
                    yield format_sse(
                        "artifact",
                        json.loads(response.generation_artifact.model_dump_json()),
                    )
                yield format_sse("complete", payload)
            except HTTPException as exc:
                yield format_sse("error", {"message": exc.detail})
            except Exception as exc:
                logger.exception("Generation stream failed")
                yield format_sse("error", {"message": str(exc)})
            return

        accumulated = ""
        start = time.perf_counter()
        record_activity(
            db,
            user_id=current_user.id,
            event_type="model_call_started",
            message="Streaming model call started.",
            conversation_id=request.conversation_id,
            metadata=with_request_meta(
                request_id=request_id,
                model=decision.model_id,
                provider=decision.provider,
                streaming=True,
            ),
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
                metadata=with_request_meta(
                    request_id=request_id,
                    provider=exc.provider,
                    streaming=True,
                ),
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
                metadata=with_request_meta(
                    request_id=request_id,
                    model=decision.model_id,
                    error=str(exc),
                    streaming=True,
                ),
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
            is_mock=not has_provider_key(db, current_user.id, decision.provider),
            provider=decision.provider,
        )

        record_activity(
            db,
            user_id=current_user.id,
            event_type="model_call_completed",
            message="Streaming model call completed.",
            conversation_id=request.conversation_id,
            metadata=with_request_meta(
                request_id=request_id,
                model=decision.model_id,
                provider=decision.provider,
                latency_ms=latency_ms,
                streaming=True,
            ),
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
                modality="chat",
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
