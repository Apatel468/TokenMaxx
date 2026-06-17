"""
Document text extraction and chunking for RAG uploads.

Supports TXT, MD, and PDF. Chunks are plain text segments with optional overlap.
"""

from __future__ import annotations

from io import BytesIO

from fastapi import HTTPException, status
from pypdf import PdfReader

SUPPORTED_FILE_TYPES = {"txt", "md", "pdf"}
DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 50
MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB


def detect_file_type(filename: str) -> str:
    """Return normalized file type from extension."""
    if "." not in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must have an extension (.txt, .md, or .pdf).",
        )
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in SUPPORTED_FILE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '.{ext}'. Use TXT, MD, or PDF.",
        )
    return ext


def extract_text(file_bytes: bytes, file_type: str) -> str:
    """Extract plain text from uploaded file bytes."""
    if file_type in {"txt", "md"}:
        try:
            text = file_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Text file must be valid UTF-8.",
            ) from exc
    elif file_type == "pdf":
        try:
            reader = PdfReader(BytesIO(file_bytes))
            pages = [page.extract_text() or "" for page in reader.pages]
            text = "\n".join(pages)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not read PDF file.",
            ) from exc
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file_type}",
        )

    cleaned = text.strip()
    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No extractable text found in document.",
        )
    return cleaned


def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[str]:
    """
    Split text into overlapping character-based chunks.

    Uses sliding windows so context is not lost at chunk boundaries.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be between 0 and chunk_size - 1")

    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = end - overlap

    return chunks
