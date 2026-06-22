"""
Generation router — history, downloads, and regeneration for documents and images.
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database import GeneratedDocument, GeneratedImage, User, get_db
from models import (
    DocumentPreviewOut,
    GeneratedDocumentOut,
    GeneratedImageOut,
    GenerationHistoryOut,
)
from services.auth_dependencies import get_current_user
from services.generation.intent import detect_generation_intent
from services.generation.preview_service import build_document_preview
from services.generation.storage import resolve_storage_path
from services.generation_service import (
    get_document_for_user,
    get_image_for_user,
    increment_download_count,
    run_document_generation,
    run_image_generation,
)
from services.model_clients import ModelResponse
from services.timezone_utils import format_timestamp_eastern
from services.chat_service import prepare_chat_turn, build_chat_response, build_routing_metadata
from services.activity_logger import new_request_id, record_activity, with_request_meta
from models import ChatRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generations", tags=["generations"])


def _document_out(row: GeneratedDocument) -> GeneratedDocumentOut:
    return GeneratedDocumentOut(
        id=row.id,
        file_name=row.file_name,
        file_type=row.file_type,
        file_size=row.file_size,
        prompt=row.prompt,
        model_used=row.model_used,
        file_count=row.file_count,
        is_archive=row.is_archive,
        download_count=row.download_count,
        created_at=format_timestamp_eastern(row.created_at),
        conversation_id=row.conversation_id,
        message_id=row.message_id,
    )


def _image_out(row: GeneratedImage) -> GeneratedImageOut:
    return GeneratedImageOut(
        id=row.id,
        image_type=row.image_type,
        prompt=row.prompt,
        provider_used=row.provider_used,
        model_used=row.model_used,
        width=row.width,
        height=row.height,
        preview_url=f"/generations/images/{row.id}/file",
        download_url=f"/generations/images/{row.id}/download",
        download_count=row.download_count,
        created_at=format_timestamp_eastern(row.created_at),
        conversation_id=row.conversation_id,
        message_id=row.message_id,
    )


@router.get("/history", response_model=GenerationHistoryOut)
def generation_history(
    q: str = Query(default="", max_length=200),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GenerationHistoryOut:
    """List user's generated documents and images with optional search."""
    doc_query = db.query(GeneratedDocument).filter(
        GeneratedDocument.user_id == current_user.id
    )
    img_query = db.query(GeneratedImage).filter(
        GeneratedImage.user_id == current_user.id
    )
    if q.strip():
        pattern = f"%{q.strip()}%"
        doc_query = doc_query.filter(GeneratedDocument.prompt.ilike(pattern))
        img_query = img_query.filter(GeneratedImage.prompt.ilike(pattern))

    docs = (
        doc_query.order_by(GeneratedDocument.created_at.desc()).limit(limit).all()
    )
    images = (
        img_query.order_by(GeneratedImage.created_at.desc()).limit(limit).all()
    )
    return GenerationHistoryOut(
        documents=[_document_out(d) for d in docs],
        images=[_image_out(i) for i in images],
    )


@router.get("/documents", response_model=list[GeneratedDocumentOut])
def list_documents(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[GeneratedDocumentOut]:
    rows = (
        db.query(GeneratedDocument)
        .filter(GeneratedDocument.user_id == current_user.id)
        .order_by(GeneratedDocument.created_at.desc())
        .limit(limit)
        .all()
    )
    return [_document_out(r) for r in rows]


@router.get("/images", response_model=list[GeneratedImageOut])
def list_images(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[GeneratedImageOut]:
    rows = (
        db.query(GeneratedImage)
        .filter(GeneratedImage.user_id == current_user.id)
        .order_by(GeneratedImage.created_at.desc())
        .limit(limit)
        .all()
    )
    return [_image_out(r) for r in rows]


@router.get("/documents/{doc_id}/preview", response_model=DocumentPreviewOut)
def preview_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentPreviewOut:
    """Return preview content for inline chat display."""
    row = get_document_for_user(db, doc_id, current_user)
    payload = build_document_preview(row.storage_path, row.file_type, row.files_json)
    return DocumentPreviewOut(**payload)


@router.get("/documents/{doc_id}/download")
def download_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = get_document_for_user(db, doc_id, current_user)
    path = resolve_storage_path(row.storage_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="File not found on disk.")
    increment_download_count(db, "document", doc_id)
    db.commit()
    return FileResponse(
        path,
        filename=row.file_name,
        media_type="application/octet-stream",
    )


@router.get("/images/{image_id}/file")
def serve_image(
    image_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = get_image_for_user(db, image_id, current_user)
    path = resolve_storage_path(row.storage_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Image not found on disk.")
    return FileResponse(path, media_type="image/png")


@router.get("/images/{image_id}/download")
def download_image(
    image_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = get_image_for_user(db, image_id, current_user)
    path = resolve_storage_path(row.storage_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Image not found on disk.")
    increment_download_count(db, "image", image_id)
    db.commit()
    filename = f"tokenmaxx_image_{image_id}.png"
    return FileResponse(path, filename=filename, media_type="image/png")


@router.post("/documents/{doc_id}/regenerate")
def regenerate_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Regenerate a previously created document from its stored prompt."""
    row = get_document_for_user(db, doc_id, current_user)
    request = ChatRequest(prompt=row.prompt, enhance_prompt=True)
    request_id = new_request_id()
    intent = detect_generation_intent(row.prompt)
    intent.modality = "document"
    intent.file_type = row.file_type
    intent.is_project = row.is_archive

    analysis, context, decision, enhancement_cost_saved, _, generation_intent = prepare_chat_turn(
        db, current_user, request, request_id=request_id
    )
    record_activity(
        db,
        user_id=current_user.id,
        event_type="document_regeneration_started",
        message="Document regeneration started.",
        metadata=with_request_meta(request_id=request_id, document_id=doc_id),
    )
    doc_result, doc_row, conv_id, title, user_msg_id, asst_msg_id, costs = (
        run_document_generation(
            db,
            current_user,
            row.prompt,
            context,
            analysis,
            decision,
            intent,
            conversation_id=row.conversation_id,
            enhancement_cost_saved=enhancement_cost_saved,
            enhance_prompt=True,
        )
    )
    db.commit()
    return build_chat_response(
        request,
        analysis,
        context,
        decision,
        doc_result.model_response or ModelResponse(
            text=doc_result.content,
            estimated_output_tokens=0,
            provider=doc_result.provider,
            litellm_model=doc_result.model_used,
        ),
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


@router.post("/images/{image_id}/regenerate")
def regenerate_image(
    image_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Regenerate a previously created image from its stored prompt."""
    row = get_image_for_user(db, image_id, current_user)
    request = ChatRequest(prompt=row.prompt, enhance_prompt=False)
    request_id = new_request_id()
    intent = detect_generation_intent(row.prompt)
    intent.modality = "image"
    intent.image_type = row.image_type

    analysis, context, decision, enhancement_cost_saved, _, generation_intent = prepare_chat_turn(
        db, current_user, request, request_id=request_id
    )
    img_result, img_row, conv_id, title, user_msg_id, asst_msg_id = (
        run_image_generation(
            db,
            current_user,
            row.prompt,
            context,
            analysis,
            decision,
            intent,
            conversation_id=row.conversation_id,
            enhancement_cost_saved=enhancement_cost_saved,
            enhance_prompt=False,
        )
    )
    db.commit()
    from services.cost_tracker import CostEstimate

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
