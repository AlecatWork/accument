"""Adding a paper to the library: read -> cut into chunks -> save -> index by meaning.

If any step fails, the paper is marked "failed" with a plain-English reason that the
My Papers page shows, instead of crashing the whole upload.
"""

from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import logger
from app.core.models import Chunk, Document
from app.repositories import chunks as chunk_repo
from app.repositories import documents as doc_repo
from app.services import embeddings
from app.services.chunker import chunk_pages
from app.services.document_parser import parse_document
from app.services.file_storage import save_file
from app.services.llm.ollama import OllamaError, embed_texts


def ingest_document(db: Session, user_id: UUID, filename: str, data: bytes) -> Document:
    """Process one uploaded file end to end and return its (ready or failed) record."""
    doc = doc_repo.create(
        db,
        user_id=user_id,
        filename=filename,
        title=Path(filename).stem,
        status="processing",
        file_path="",
    )
    try:
        doc.file_path = save_file(user_id, doc.id, filename, data)
        pages = parse_document(filename, data)
        doc.page_count = len(pages)
        pieces = chunk_pages(pages)
        if not pieces:
            raise ValueError("No readable text found. Scanned (picture-only) files can't be read yet.")

        rows = chunk_repo.add_many(
            db,
            [
                Chunk(
                    document_id=doc.id,
                    page_number=p["page_number"],
                    chunk_index=p["chunk_index"],
                    text=p["text"],
                )
                for p in pieces
            ],
        )
        vectors = embed_texts([r.text for r in rows])
        embeddings.add_chunks(
            ids=[str(r.id) for r in rows],
            texts=[r.text for r in rows],
            embeddings=vectors,
            metadatas=[
                {
                    "document_id": str(doc.id),
                    "user_id": str(user_id),
                    "page_number": r.page_number,
                    "chunk_id": str(r.id),
                }
                for r in rows
            ],
        )
        doc.status = "ready"
        doc.error_message = None
    except (OllamaError, ValueError) as exc:  # problems we understand: show the message as-is
        logger.warning("Could not ingest %s: %s", filename, exc)
        doc.status = "failed"
        doc.error_message = str(exc)
    except Exception:  # anything unexpected: log the details, show a gentle message
        logger.exception("Failed to ingest %s", filename)
        doc.status = "failed"
        doc.error_message = "We couldn't read this file. It may be damaged or in an unsupported layout."
    return doc_repo.save(db, doc)
