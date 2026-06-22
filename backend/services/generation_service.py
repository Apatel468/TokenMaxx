"""
Generation orchestration — persist artifacts, link to conversations, history.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from database import GeneratedDocument, GeneratedImage, Message, User
from services.context_builder import PromptContext
from services.cost_tracker import CostEstimate, estimate_costs
from services.generation.document_generator import DocumentGenerationResult, generate_document
from services.generation.image_generator import ImageGenerationResult, generate_image
from services.generation.intent import GenerationIntent
from services.generation.storage import relative_storage_path
from services.model_clients import ModelResponse
from services.prompt_analyzer import AnalysisResult
from services.router_engine import RoutingDecision
from services.conversation_store import save_chat_turn

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def persist_generated_document(
    db: Session,
    user_id: int,
    prompt: str,
    result: DocumentGenerationResult,
    *,
    conversation_id: int | None = None,
    message_id: int | None = None,
) -> GeneratedDocument:
    row = GeneratedDocument(
        user_id=user_id,
        conversation_id=conversation_id,
        message_id=message_id,
        file_name=result.file_name,
        file_type=result.file_type,
        file_size=result.file_size,
        storage_path=relative_storage_path(result.storage_path),
        prompt=prompt,
        model_used=result.model_used,
        file_count=result.file_count,
        is_archive=result.is_archive,
        files_json=json.dumps(
            [{"name": f.name, "path": f.path, "size": f.size_bytes} for f in result.files]
        ),
    )
    db.add(row)
    db.flush()
    return row


def persist_generated_image(
    db: Session,
    user_id: int,
    prompt: str,
    result: ImageGenerationResult,
    *,
    conversation_id: int | None = None,
    message_id: int | None = None,
) -> GeneratedImage:
    row = GeneratedImage(
        user_id=user_id,
        conversation_id=conversation_id,
        message_id=message_id,
        image_type=result.image_type,
        prompt=prompt,
        provider_used=result.provider_used,
        model_used=result.model_used,
        storage_path=relative_storage_path(result.storage_path),
        width=result.width,
        height=result.height,
        revised_prompt=result.revised_prompt or None,
    )
    db.add(row)
    db.flush()
    return row


def run_document_generation(
    db: Session,
    user: User,
    request_prompt: str,
    context: PromptContext,
    analysis: AnalysisResult,
    decision: RoutingDecision,
    intent: GenerationIntent,
    *,
    conversation_id: int | None = None,
    enhancement_cost_saved: float = 0.0,
    enhance_prompt: bool = True,
) -> tuple[DocumentGenerationResult, GeneratedDocument, int, str, int, int, CostEstimate]:
    """Generate document, save chat turn, persist artifact."""
    doc_result = generate_document(
        context,
        decision.model_id,
        file_type=intent.file_type or "txt",
        is_project=intent.is_project,
        db=db,
        user_id=user.id,
    )

    model_response = doc_result.model_response or ModelResponse(
        text=doc_result.content,
        estimated_output_tokens=0,
        provider=doc_result.provider,
        litellm_model=doc_result.model_used,
    )
    costs = estimate_costs(decision.model_id, context, model_response)

    summary = (
        f"Generated **{doc_result.file_name}** ({doc_result.file_type.upper()}, "
        f"{doc_result.file_size:,} bytes).\n\n"
        f"Download your file using the button below."
    )

    conv_id, title, user_msg_id, asst_msg_id = save_chat_turn(
        db=db,
        prompt=request_prompt,
        response_text=summary,
        task_type=context.task_type,
        decision=decision,
        model_response=model_response,
        costs=costs,
        user_id=user.id,
        conversation_id=conversation_id,
        enhanced_prompt=context.enhanced_prompt,
        system_prompt=context.system_prompt or "",
        enhancement_reason=context.enhancement_reason,
        enhancement_method=context.enhancement_method,
        enhancement_enabled=enhance_prompt,
        enhancement_cost_saved=enhancement_cost_saved,
        classification_method=analysis.classification_method,
        classification_reason=analysis.classification_reason,
        classification_confidence=analysis.confidence,
        prompt_analysis=context.prompt_analysis,
        rag_used=context.rag_used,
        rag_chunk_count=context.retrieved_chunk_count,
        rag_source_documents=context.source_documents,
        rag_source_filenames=context.source_filenames,
        content_type="document",
        generation_artifact_type="document",
    )

    asst = db.query(Message).filter(Message.id == asst_msg_id).first()
    if asst:
        asst.generation_artifact_type = "document"

    doc_row = persist_generated_document(
        db,
        user.id,
        request_prompt,
        doc_result,
        conversation_id=conv_id,
        message_id=asst_msg_id,
    )
    if asst:
        asst.generation_artifact_id = doc_row.id

    return doc_result, doc_row, conv_id, title or "", user_msg_id, asst_msg_id, costs


def run_image_generation(
    db: Session,
    user: User,
    request_prompt: str,
    context: PromptContext,
    analysis: AnalysisResult,
    decision: RoutingDecision,
    intent: GenerationIntent,
    *,
    conversation_id: int | None = None,
    enhancement_cost_saved: float = 0.0,
    enhance_prompt: bool = True,
) -> tuple[ImageGenerationResult, GeneratedImage, int, str, int, int]:
    """Generate image, save chat turn, persist artifact."""
    img_result = generate_image(
        request_prompt,
        image_type=intent.image_type or "general",
        db=db,
        user_id=user.id,
    )

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

    summary = (
        f"Generated **{intent.image_type or 'image'}** "
        f"({img_result.width}×{img_result.height}px via {img_result.provider_used})."
    )

    conv_id, title, user_msg_id, asst_msg_id = save_chat_turn(
        db=db,
        prompt=request_prompt,
        response_text=summary,
        task_type=context.task_type,
        decision=decision,
        model_response=model_response,
        costs=costs,
        user_id=user.id,
        conversation_id=conversation_id,
        enhanced_prompt=context.enhanced_prompt,
        system_prompt=context.system_prompt or "",
        enhancement_reason=context.enhancement_reason,
        enhancement_method=context.enhancement_method,
        enhancement_enabled=enhance_prompt,
        enhancement_cost_saved=enhancement_cost_saved,
        classification_method=analysis.classification_method,
        classification_reason=analysis.classification_reason,
        classification_confidence=analysis.confidence,
        prompt_analysis=context.prompt_analysis,
        rag_used=context.rag_used,
        rag_chunk_count=context.retrieved_chunk_count,
        rag_source_documents=context.source_documents,
        rag_source_filenames=context.source_filenames,
        content_type="image",
        generation_artifact_type="image",
    )

    asst = db.query(Message).filter(Message.id == asst_msg_id).first()
    if asst:
        asst.generation_artifact_type = "image"

    img_row = persist_generated_image(
        db,
        user.id,
        request_prompt,
        img_result,
        conversation_id=conv_id,
        message_id=asst_msg_id,
    )
    if asst:
        asst.generation_artifact_id = img_row.id

    return img_result, img_row, conv_id, title or "", user_msg_id, asst_msg_id


def get_document_for_user(db: Session, doc_id: int, user: User) -> GeneratedDocument:
    row = db.query(GeneratedDocument).filter(GeneratedDocument.id == doc_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Generated document not found.")
    if row.user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Not your document.")
    return row


def get_image_for_user(db: Session, image_id: int, user: User) -> GeneratedImage:
    row = db.query(GeneratedImage).filter(GeneratedImage.id == image_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Generated image not found.")
    if row.user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Not your image.")
    return row


def increment_download_count(db: Session, artifact_type: str, artifact_id: int) -> None:
    if artifact_type == "document":
        row = db.query(GeneratedDocument).filter(GeneratedDocument.id == artifact_id).first()
    else:
        row = db.query(GeneratedImage).filter(GeneratedImage.id == artifact_id).first()
    if row:
        row.download_count = (row.download_count or 0) + 1
