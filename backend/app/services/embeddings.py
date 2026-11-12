"""The "librarian": ChromaDB, a special database that finds passages by MEANING.

We store every chunk together with its meaning-numbers. Later we hand it the meaning-numbers
of a question and it returns the closest chunks.
"""

import chromadb

from app.config import settings

_client = None
_collection = None


def get_collection():
    """Open (or create) the shelf where chunks are kept. Done once, then reused."""
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(path=settings.chroma_path)
        try:
            # Newer ChromaDB versions: say "compare by angle between meaning-numbers" (cosine).
            _collection = _client.get_or_create_collection(
                name="accument_chunks", configuration={"hnsw": {"space": "cosine"}}
            )
        except TypeError:
            # Older versions use a different setting name for the same idea.
            _collection = _client.get_or_create_collection(
                name="accument_chunks", metadata={"hnsw:space": "cosine"}
            )
    return _collection


def add_chunks(ids: list[str], texts: list[str], embeddings: list[list[float]], metadatas: list[dict]) -> None:
    """File chunks on the shelf, each with its meaning-numbers and a label (which paper, which page)."""
    get_collection().add(ids=ids, documents=texts, embeddings=embeddings, metadatas=metadatas)


def delete_document(document_id: str) -> None:
    """Take every chunk of one paper off the shelf. Never crashes: a missing shelf just means nothing to delete."""
    try:
        get_collection().delete(where={"document_id": document_id})
    except Exception:
        pass
