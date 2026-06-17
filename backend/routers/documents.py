"""
Documents router — upload, list, search, and delete user documents (Phase 1 RAG).

Chunks are stored in ChromaDB; metadata lives in SQLite uploaded_documents.
Not wired to chat yet.
"""

from __future__ import annotations

from datetime import timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from database import UploadedDocument, User, get_db
from models import (
    DocumentOut,
    DocumentSearchRequest,
    DocumentSearchResult,
    DocumentUploadResponse,
)
from services import vector_store
from services.auth_dependencies import get_current_user
from services.activity_logger import record_activity
from services.document_processor import (
    MAX_FILE_BYTES,
    chunk_text,
    detect_file_type,
    extract_text,
)

router = APIRouter(prefix="/documents", tags=["documents"])


def _format_created_at(dt) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _to_document_out(row: UploadedDocument) -> DocumentOut:
    return DocumentOut(
        id=row.id,
        filename=row.filename,
        file_type=row.file_type,
        chunk_count=row.chunk_count,
        created_at=_format_created_at(row.created_at),
    )


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentUploadResponse:
    """Upload a TXT, MD, or PDF document; chunk and index in ChromaDB."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required.",
        )

    file_type = detect_file_type(file.filename)
    record_activity(
        db,
        user_id=current_user.id,
        event_type="document_upload_started",
        message="Document upload started.",
        metadata={"filename": file.filename, "file_type": file_type},
    )
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )
    if len(file_bytes) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File exceeds 10 MB limit.",
        )

    text = extract_text(file_bytes, file_type)
    chunks = chunk_text(text)

    document = UploadedDocument(
        user_id=current_user.id,
        filename=file.filename,
        file_type=file_type,
        chunk_count=len(chunks),
    )
    db.add(document)
    db.flush()

    try:
        vector_store.add_document_chunks(
            document_id=document.id,
            user_id=current_user.id,
            filename=file.filename,
            chunks=chunks,
        )
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to index document chunks.",
        ) from exc

    db.commit()
    db.refresh(document)
    record_activity(
        db,
        user_id=current_user.id,
        event_type="document_indexed",
        message="Document indexed and ready for RAG.",
        metadata={
            "document_id": document.id,
            "filename": document.filename,
            "chunk_count": document.chunk_count,
        },
    )
    db.commit()
    return DocumentUploadResponse(document=_to_document_out(document))


@router.get("", response_model=list[DocumentOut])
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[DocumentOut]:
    """List uploaded documents for the logged-in user."""
    rows = (
        db.query(UploadedDocument)
        .filter(UploadedDocument.user_id == current_user.id)
        .order_by(UploadedDocument.created_at.desc())
        .all()
    )
    return [_to_document_out(row) for row in rows]


@router.post("/search", response_model=list[DocumentSearchResult])
def search_documents(
    body: DocumentSearchRequest,
    current_user: User = Depends(get_current_user),
) -> list[DocumentSearchResult]:
    """Semantic search over the current user's uploaded chunks."""
    hits = vector_store.search_user_chunks(
        user_id=current_user.id,
        query=body.query.strip(),
        top_k=5,
    )
    return [DocumentSearchResult(**hit) for hit in hits]


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete document metadata and all associated vector chunks."""
    document = (
        db.query(UploadedDocument)
        .filter(
            UploadedDocument.id == document_id,
            UploadedDocument.user_id == current_user.id,
        )
        .first()
    )
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    vector_store.delete_document_chunks(document_id)
    db.delete(document)
    db.commit()
