"""
ChromaDB vector store for document chunk embeddings.

Persists locally under CHROMA_PERSIST_DIR (default: backend/chroma_data/).
SQLite holds document metadata; Chroma holds chunk text + embeddings.
"""

from __future__ import annotations

import os
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

COLLECTION_NAME = "document_chunks"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

_client: chromadb.PersistentClient | None = None
_collection = None


def _default_persist_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "chroma_data"


def get_persist_dir() -> Path:
    """Resolve Chroma persistence directory from env or default."""
    raw = os.getenv("CHROMA_PERSIST_DIR", "").strip()
    path = Path(raw) if raw else _default_persist_dir()
    path.mkdir(parents=True, exist_ok=True)
    return path


def reset_vector_store() -> None:
    """Clear cached client/collection (used in tests)."""
    global _client, _collection
    _client = None
    _collection = None


def _get_collection():
    global _client, _collection
    if _collection is not None:
        return _collection

    persist_dir = get_persist_dir()
    _client = chromadb.PersistentClient(path=str(persist_dir))
    embedding_fn = SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)
    _collection = _client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"},
    )
    return _collection


def add_document_chunks(
    *,
    document_id: int,
    user_id: int,
    filename: str,
    chunks: list[str],
) -> None:
    """Embed and store chunks for one uploaded document."""
    if not chunks:
        return

    collection = _get_collection()
    ids = [f"{document_id}_{index}" for index in range(len(chunks))]
    metadatas = [
        {
            "user_id": user_id,
            "document_id": document_id,
            "filename": filename,
            "chunk_index": index,
        }
        for index in range(len(chunks))
    ]
    collection.add(ids=ids, documents=chunks, metadatas=metadatas)


def search_user_chunks(
    *,
    user_id: int,
    query: str,
    top_k: int = 5,
) -> list[dict]:
    """
    Semantic search over one user's chunks.

    Returns dicts with text, filename, chunk_index, document_id, similarity_score.
    """
    collection = _get_collection()
    result = collection.query(
        query_texts=[query],
        n_results=top_k,
        where={"user_id": user_id},
        include=["documents", "metadatas", "distances"],
    )

    documents = (result.get("documents") or [[]])[0]
    metadatas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]

    hits: list[dict] = []
    for doc, meta, distance in zip(documents, metadatas, distances):
        if not doc or not meta:
            continue
        # Cosine distance in [0, 2]; convert to similarity in [0, 1]
        similarity = max(0.0, 1.0 - float(distance))
        hits.append(
            {
                "text": doc,
                "filename": meta["filename"],
                "chunk_index": int(meta["chunk_index"]),
                "document_id": int(meta["document_id"]),
                "similarity_score": round(similarity, 4),
            }
        )
    return hits


def delete_document_chunks(document_id: int) -> None:
    """Remove all vector chunks for a document."""
    collection = _get_collection()
    collection.delete(where={"document_id": document_id})
