"""
RAG service — retrieve document chunks and inject into chat context.

Phase 2: connects ChromaDB search to the chat pipeline without replacing SQLite.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field

from services.context_builder import PromptContext
from services import vector_store

logger = logging.getLogger(__name__)

RAG_TOP_K = 3
DEFAULT_SIMILARITY_THRESHOLD = 0.4

_RAG_INSTRUCTIONS = (
    "Use the uploaded document context below when it is relevant to the user's question. "
    "If the answer is not found in the uploaded documents, clearly state that the "
    "uploaded documents do not contain enough information. "
    "Do not invent facts that are not supported by the document context or conversation."
)


def get_similarity_threshold() -> float:
    raw = os.getenv("RAG_SIMILARITY_THRESHOLD", "").strip()
    if not raw:
        return DEFAULT_SIMILARITY_THRESHOLD
    try:
        return float(raw)
    except ValueError:
        return DEFAULT_SIMILARITY_THRESHOLD


@dataclass
class RagResult:
    """Outcome of a chat-time document retrieval."""

    rag_used: bool = False
    retrieved_chunk_count: int = 0
    source_documents: list[int] = field(default_factory=list)
    source_filenames: list[str] = field(default_factory=list)
    context_block: str = ""


def retrieve_for_chat(user_id: int, query: str) -> RagResult:
    """
    Search the user's uploaded documents for chunks relevant to the chat prompt.

    Returns empty RagResult when no chunks meet the similarity threshold.
    """
    query = query.strip()
    if not query:
        return RagResult()

    try:
        hits = vector_store.search_user_chunks(
            user_id=user_id,
            query=query,
            top_k=RAG_TOP_K,
        )
    except Exception as exc:
        logger.warning("RAG retrieval failed for user %s: %s", user_id, exc)
        return RagResult()

    threshold = get_similarity_threshold()
    relevant = [hit for hit in hits if hit["similarity_score"] >= threshold]
    if not relevant:
        return RagResult()

    context_block = _build_context_block(relevant)
    document_ids: list[int] = []
    filenames: list[str] = []
    for hit in relevant:
        doc_id = hit["document_id"]
        if doc_id not in document_ids:
            document_ids.append(doc_id)
        name = hit["filename"]
        if name not in filenames:
            filenames.append(name)

    return RagResult(
        rag_used=True,
        retrieved_chunk_count=len(relevant),
        source_documents=document_ids,
        source_filenames=filenames,
        context_block=context_block,
    )


def _build_context_block(chunks: list[dict]) -> str:
    lines = ["Relevant uploaded document context:"]
    for hit in chunks:
        chunk_num = hit["chunk_index"] + 1
        lines.append(f"[Source: {hit['filename']}, chunk {chunk_num}]")
        lines.append(hit["text"])
        lines.append("")
    return "\n".join(lines).strip()


def apply_rag_to_context(context: PromptContext, rag: RagResult) -> PromptContext:
    """Append RAG instructions and retrieved chunks to the system prompt."""
    if not rag.rag_used or not rag.context_block:
        return context

    rag_section = f"{_RAG_INSTRUCTIONS}\n\n{rag.context_block}"
    if context.system_prompt:
        system_prompt = f"{context.system_prompt.strip()}\n\n{rag_section}"
    else:
        system_prompt = rag_section

    extra_chars = len(rag_section)
    estimated_tokens = context.estimated_input_tokens + max(extra_chars // 4, 0)

    context.system_prompt = system_prompt
    context.rag_used = True
    context.retrieved_chunk_count = rag.retrieved_chunk_count
    context.source_documents = list(rag.source_documents)
    context.source_filenames = list(rag.source_filenames)
    context.estimated_input_tokens = estimated_tokens
    return context


def rag_metadata_dict(context: PromptContext) -> dict:
    """API-friendly RAG fields from a prepared context."""
    return {
        "rag_used": context.rag_used,
        "retrieved_chunk_count": context.retrieved_chunk_count,
        "source_documents": context.source_documents,
        "source_filenames": context.source_filenames,
    }


def serialize_source_documents(document_ids: list[int]) -> str | None:
    if not document_ids:
        return None
    return json.dumps(document_ids)


def serialize_source_filenames(filenames: list[str]) -> str | None:
    if not filenames:
        return None
    return json.dumps(filenames)


def deserialize_source_documents(raw: str | None) -> list[int]:
    if not raw:
        return []
    try:
        return [int(x) for x in json.loads(raw)]
    except (json.JSONDecodeError, TypeError, ValueError):
        return []


def deserialize_source_filenames(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        return list(json.loads(raw))
    except (json.JSONDecodeError, TypeError):
        return []
