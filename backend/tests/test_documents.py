"""
Tests for document upload, list, search, isolation, and delete (Phase 1 RAG).
"""

from __future__ import annotations

from io import BytesIO

from tests.conftest import auth_headers


def _signup(client, email: str) -> str:
    response = client.post(
        "/auth/signup",
        json={"email": email, "password": "testpass123"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def _upload_txt(client, token: str, filename: str, content: str):
    return client.post(
        "/documents/upload",
        headers=auth_headers(token),
        files={"file": (filename, BytesIO(content.encode("utf-8")), "text/plain")},
    )


def test_upload_txt_document(client, auth_token):
    response = _upload_txt(
        client,
        auth_token,
        "notes.txt",
        "TokenMaxx routes prompts to cost-effective Groq models. "
        "RAG stores document chunks in ChromaDB for semantic search.",
    )
    assert response.status_code == 200
    body = response.json()["document"]
    assert body["filename"] == "notes.txt"
    assert body["file_type"] == "txt"
    assert body["chunk_count"] >= 1
    assert body["id"] > 0


def test_list_documents(client, auth_token):
    _upload_txt(client, auth_token, "alpha.txt", "Alpha document about routing.")
    _upload_txt(client, auth_token, "beta.txt", "Beta document about analytics.")

    response = client.get("/documents", headers=auth_headers(auth_token))
    assert response.status_code == 200
    docs = response.json()
    assert len(docs) == 2
    filenames = {doc["filename"] for doc in docs}
    assert filenames == {"alpha.txt", "beta.txt"}


def test_search_returns_relevant_chunks(client, auth_token):
    _upload_txt(
        client,
        auth_token,
        "rag-guide.txt",
        "ChromaDB stores vector embeddings for uploaded documents. "
        "Semantic search finds the most relevant text chunks for a query.",
    )

    response = client.post(
        "/documents/search",
        json={"query": "vector embeddings semantic search"},
        headers=auth_headers(auth_token),
    )
    assert response.status_code == 200
    hits = response.json()
    assert len(hits) >= 1
    assert hits[0]["filename"] == "rag-guide.txt"
    assert hits[0]["similarity_score"] > 0
    assert "ChromaDB" in hits[0]["text"] or "semantic" in hits[0]["text"].lower()


def test_users_cannot_access_other_users_chunks(client):
    user_a = _signup(client, "user-a@example.com")
    user_b = _signup(client, "user-b@example.com")

    upload = _upload_txt(
        client,
        user_a,
        "private.txt",
        "Confidential routing strategy for user A only.",
    )
    assert upload.status_code == 200
    document_id = upload.json()["document"]["id"]

    search_b = client.post(
        "/documents/search",
        json={"query": "confidential routing strategy"},
        headers=auth_headers(user_b),
    )
    assert search_b.status_code == 200
    assert search_b.json() == []

    list_b = client.get("/documents", headers=auth_headers(user_b))
    assert list_b.status_code == 200
    assert list_b.json() == []

    delete_b = client.delete(
        f"/documents/{document_id}",
        headers=auth_headers(user_b),
    )
    assert delete_b.status_code == 404

    search_a = client.post(
        "/documents/search",
        json={"query": "confidential routing strategy"},
        headers=auth_headers(user_a),
    )
    assert search_a.status_code == 200
    assert len(search_a.json()) >= 1


def test_delete_removes_metadata_and_vector_chunks(client, auth_token):
    upload = _upload_txt(
        client,
        auth_token,
        "temp.txt",
        "Temporary document about delete flow and chunk cleanup.",
    )
    assert upload.status_code == 200
    document_id = upload.json()["document"]["id"]

    search_before = client.post(
        "/documents/search",
        json={"query": "delete flow chunk cleanup"},
        headers=auth_headers(auth_token),
    )
    assert search_before.status_code == 200
    assert len(search_before.json()) >= 1

    delete_response = client.delete(
        f"/documents/{document_id}",
        headers=auth_headers(auth_token),
    )
    assert delete_response.status_code == 204

    list_response = client.get("/documents", headers=auth_headers(auth_token))
    assert list_response.status_code == 200
    assert list_response.json() == []

    search_after = client.post(
        "/documents/search",
        json={"query": "delete flow chunk cleanup"},
        headers=auth_headers(auth_token),
    )
    assert search_after.status_code == 200
    assert search_after.json() == []


def test_upload_requires_auth(client):
    response = client.post(
        "/documents/upload",
        files={"file": ("notes.txt", BytesIO(b"hello"), "text/plain")},
    )
    assert response.status_code == 401
