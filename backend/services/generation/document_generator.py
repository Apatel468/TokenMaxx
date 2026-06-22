"""
Document generation — LLM content + file rendering.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from services.context_builder import PromptContext
from services.generation.document_writer import write_document_file
from services.generation.format_registry import default_basename
from services.generation.storage import document_storage_path, file_size_bytes
from services.model_clients import ModelResponse, generate_response

logger = logging.getLogger(__name__)

_PROJECT_SYSTEM = (
    "You are a software architect. Generate a complete project as multiple files. "
    "Use this exact format for each file:\n"
    "=== relative/path/to/file.ext ===\n"
    "file content here\n\n"
    "Include README.md and all necessary source files. Output only file blocks."
)

_DOCUMENT_SYSTEM = (
    "You are a professional technical writer. Generate the complete document content "
    "requested by the user. Output only the document body — no preamble or explanation. "
    "Use appropriate structure (headings, sections, code blocks) for the format."
)


@dataclass
class DocumentFileInfo:
    """One file in a generation result."""

    path: str
    name: str
    file_type: str
    size_bytes: int


@dataclass
class DocumentGenerationResult:
    """Result of document generation."""

    content: str
    file_name: str
    file_type: str
    mime_type: str
    storage_path: str
    file_size: int
    file_count: int = 1
    is_archive: bool = False
    files: list[DocumentFileInfo] = field(default_factory=list)
    model_used: str = ""
    provider: str = "groq"
    latency_ms: float = 0.0
    is_mock: bool = False
    model_response: ModelResponse | None = None


def _build_filename(prompt: str, file_type: str, is_project: bool) -> str:
    ext = file_type.lower().lstrip(".")
    if is_project or ext == "zip":
        return f"tokenmaxx_project.{ext if ext == 'zip' else 'zip'}"
    base = default_basename(ext)
    # Try to extract a name from prompt
    import re

    name_match = re.search(
        r"(?:called|named|title[d]?)\s+[\"']?([a-zA-Z0-9_\-\s]+)[\"']?",
        prompt,
        re.I,
    )
    if name_match:
        slug = re.sub(r"[^\w\-]+", "_", name_match.group(1).strip())[:40]
        if slug:
            return f"{slug}.{ext}"
    return f"{base}.{ext}"


def _document_system_prompt(file_type: str, is_project: bool) -> str:
    if is_project:
        return _PROJECT_SYSTEM
    return (
        f"{_DOCUMENT_SYSTEM}\nTarget format: .{file_type}\n"
        "Deliver production-ready content suitable for direct export."
    )


def generate_document(
    context: PromptContext,
    model_id: str,
    *,
    file_type: str,
    is_project: bool = False,
    db: Session | None = None,
    user_id: int | None = None,
) -> DocumentGenerationResult:
    """Generate document content via LLM and write to storage."""
    start = time.perf_counter()

    doc_context = PromptContext(
        prompt=context.prompt,
        task_type=context.task_type,
        confidence=context.confidence,
        estimated_input_tokens=context.estimated_input_tokens,
        is_long_prompt=context.is_long_prompt,
        keywords_matched=context.keywords_matched,
        enhanced_prompt=context.enhanced_prompt or context.prompt,
        system_prompt=_document_system_prompt(file_type, is_project),
        enhancement_reason=context.enhancement_reason,
        enhancement_method=context.enhancement_method,
        message_history=context.message_history,
    )

    model_response = generate_response(
        model_id,
        doc_context,
        messages=doc_context.message_history,
        db=db,
        user_id=user_id,
    )

    file_name = _build_filename(context.prompt, file_type, is_project)
    storage = document_storage_path(user_id or 0, file_name)

    final_path, mime_type, file_count = write_document_file(
        storage,
        model_response.text,
        file_type,
        title=file_name.rsplit(".", 1)[0],
        is_project=is_project,
    )

    latency_ms = (time.perf_counter() - start) * 1000
    size = file_size_bytes(final_path)

    files_info = [
        DocumentFileInfo(
            path=str(final_path.name),
            name=final_path.name,
            file_type=file_type,
            size_bytes=size,
        )
    ]

    return DocumentGenerationResult(
        content=model_response.text[:500] + ("…" if len(model_response.text) > 500 else ""),
        file_name=final_path.name,
        file_type=file_type,
        mime_type=mime_type,
        storage_path=str(final_path),
        file_size=size,
        file_count=file_count,
        is_archive=is_project or file_type == "zip",
        files=files_info,
        model_used=model_id,
        provider=model_response.provider,
        latency_ms=round(latency_ms, 1),
        is_mock=model_response.is_mock,
        model_response=model_response,
    )
