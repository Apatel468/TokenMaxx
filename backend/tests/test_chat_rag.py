"""
Tests for RAG integration in chat (Phase 2).

Vector retrieval is mocked — no ChromaDB or sentence-transformers required.
"""

from __future__ import annotations

import json

from services.rag_service import RagResult
from tests.conftest import auth_headers


def _mock_rag_hits(monkeypatch, hits: list[dict] | None = None):
    """Patch retrieve_for_chat to return controlled RAG results."""
    import services.chat_service as chat_service

    if hits is None:
        rag = RagResult()
    else:
        from services.rag_service import _build_context_block

        rag = RagResult(
            rag_used=True,
            retrieved_chunk_count=len(hits),
            source_documents=sorted({h["document_id"] for h in hits}),
            source_filenames=sorted({h["filename"] for h in hits}),
            context_block=_build_context_block(hits),
        )

    monkeypatch.setattr(chat_service, "retrieve_for_chat", lambda user_id, query: rag)
    return rag


def test_chat_with_relevant_document_chunks(client, auth_token, monkeypatch):
    _mock_rag_hits(
        monkeypatch,
        [
            {
                "text": "TokenMaxx pricing is $10 per seat per month.",
                "filename": "pricing.txt",
                "chunk_index": 0,
                "document_id": 7,
                "similarity_score": 0.82,
            }
        ],
    )

    response = client.post(
        "/chat",
        json={"prompt": "What is TokenMaxx pricing?", "enhance_prompt": False},
        headers=auth_headers(auth_token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["rag_used"] is True
    assert body["retrieved_chunk_count"] == 1
    assert body["source_filenames"] == ["pricing.txt"]
    assert 7 in body["source_documents"]
    assert body["mock_response"] == "Mocked LLM response for testing."


def test_chat_with_no_relevant_chunks(client, auth_token, monkeypatch):
    _mock_rag_hits(monkeypatch, hits=None)

    response = client.post(
        "/chat",
        json={"prompt": "Unrelated question about weather.", "enhance_prompt": False},
        headers=auth_headers(auth_token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["rag_used"] is False
    assert body["retrieved_chunk_count"] == 0
    assert body["source_filenames"] == []
    assert body["source_documents"] == []


def test_chat_stream_includes_rag_in_routing_and_complete(client, auth_token, monkeypatch):
    _mock_rag_hits(
        monkeypatch,
        [
            {
                "text": "Our refund policy allows returns within 30 days.",
                "filename": "policy.md",
                "chunk_index": 1,
                "document_id": 3,
                "similarity_score": 0.75,
            }
        ],
    )

    with client.stream(
        "POST",
        "/chat/stream",
        json={"prompt": "What is the refund policy?", "enhance_prompt": False},
        headers=auth_headers(auth_token),
    ) as response:
        assert response.status_code == 200
        body = response.read().decode("utf-8")

    events = []
    for block in body.split("\n\n"):
        if not block.strip():
            continue
        event_type = "message"
        data = ""
        for line in block.split("\n"):
            if line.startswith("event:"):
                event_type = line[6:].strip()
            elif line.startswith("data:"):
                data += line[5:].strip()
        if data:
            events.append((event_type, json.loads(data)))

    routing = next(data for name, data in events if name == "routing_complete")
    assert routing["rag_used"] is True
    assert routing["source_filenames"] == ["policy.md"]

    complete = next(data for name, data in events if name == "complete")
    assert complete["rag_used"] is True
    assert complete["retrieved_chunk_count"] == 1


def test_rag_retrieval_filters_by_similarity_threshold(monkeypatch):
    import services.rag_service as rag_service

    monkeypatch.setattr(
        rag_service.vector_store,
        "search_user_chunks",
        lambda **kwargs: [
            {
                "text": "weak match",
                "filename": "notes.txt",
                "chunk_index": 0,
                "document_id": 1,
                "similarity_score": 0.1,
            }
        ],
    )

    result = rag_service.retrieve_for_chat(user_id=1, query="something else")
    assert result.rag_used is False


def test_rag_apply_updates_system_prompt():
    from services.context_builder import PromptContext
    from services.rag_service import RagResult, apply_rag_to_context

    context = PromptContext(
        prompt="question",
        task_type="general_qa",
        confidence=0.9,
        estimated_input_tokens=10,
        is_long_prompt=False,
        keywords_matched=[],
        system_prompt="You are helpful.",
    )
    rag = RagResult(
        rag_used=True,
        retrieved_chunk_count=1,
        source_documents=[1],
        source_filenames=["doc.txt"],
        context_block="[Source: doc.txt, chunk 1]\nImportant fact.",
    )

    updated = apply_rag_to_context(context, rag)
    assert updated.rag_used is True
    assert "uploaded document context" in updated.system_prompt.lower()
    assert "do not contain enough information" in updated.system_prompt.lower()
    assert "Important fact." in updated.system_prompt
