"""Fill the app with demo data: a demo account, five sample papers, notes, chats and thumbs.

Run it once the app is up (Ollama must be open, because each paper gets indexed):

    docker compose exec backend python -m scripts.seed_demo_data

Safe to run again: papers that already exist are skipped.
Log in with   demo@example.com  /  demodemo123
"""

import io
import random
from datetime import timedelta

import pymupdf
from docx import Document as WordDocument
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.models import Conversation, Message, QueryLog, utc_now
from app.core.security import hash_password
from app.repositories import chunks as chunk_repo
from app.repositories import conversations as chat_repo
from app.repositories import documents as doc_repo
from app.repositories import notes as note_repo
from app.repositories import users as user_repo
from app.services.citations import number_chunks
from app.services.ingestion import ingest_document
from scripts.sample_papers import SAMPLES

EMAIL = "demo@example.com"
PASSWORD = "demodemo123"


def make_pdf(pages: list[str]) -> bytes:
    """Build a real PDF in memory, one page per string."""
    doc = pymupdf.open()
    for text in pages:
        page = doc.new_page()
        page.insert_textbox(pymupdf.Rect(72, 72, 540, 770), text, fontsize=11)
    data = doc.tobytes()
    doc.close()
    return data


def make_docx(text: str) -> bytes:
    """Build a real Word file in memory. The first paragraph becomes the title."""
    doc = WordDocument()
    first, *rest = text.split("\n\n")
    doc.add_heading(first, level=0)
    for paragraph in rest:
        doc.add_paragraph(paragraph)
    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def build_file(sample: dict) -> bytes:
    """Turn a sample definition into the bytes of a real file in its format."""
    if sample["format"] == "pdf":
        return make_pdf(sample["pages"])
    if sample["format"] == "docx":
        return make_docx(sample["text"])
    return sample["text"].encode("utf-8")  # md and html are just text


def add_demo_chats(db: Session, user_id, doc, sample: dict, rng: random.Random) -> None:
    """Create example conversations with believable timestamps, sources, speeds and thumbs."""
    chunks = chunk_repo.list_for_document(db, doc.id)
    for question, answer, page, days_ago, thumbs in sample["chats"]:
        # Use the real first excerpt from the page the answer "came from".
        chunk = next((c for c in chunks if c.page_number == page), chunks[0])
        sources = number_chunks([chunk])
        asked = utc_now() - timedelta(days=days_ago, hours=rng.randint(0, 8), minutes=rng.randint(0, 59))

        convo = Conversation(user_id=user_id, document_id=doc.id, title=question[:80], created_at=asked, updated_at=asked)
        db.add(convo)
        db.flush()
        db.add(Message(conversation_id=convo.id, role="user", content=question, created_at=asked))
        reply = Message(
            conversation_id=convo.id,
            role="assistant",
            content=answer,
            sources=sources,
            created_at=asked + timedelta(seconds=25),
        )
        db.add(reply)
        db.add(
            QueryLog(
                user_id=user_id,
                document_id=doc.id,
                question=question,
                answer=answer,
                retrieved_chunk_ids=[s["chunk_id"] for s in sources],
                latency_ms=rng.randint(9000, 45000),  # realistic for a laptop without a graphics card
                prompt_tokens=rng.randint(350, 900),
                completion_tokens=rng.randint(20, 80),
                created_at=asked,
            )
        )
        db.commit()
        if thumbs:
            chat_repo.upsert_feedback(db, reply.id, user_id, thumbs, None)


def seed(db: Session) -> None:
    """Create the demo user and any sample papers that are missing."""
    rng = random.Random(7)  # fixed seed: the same "random" history every time
    user = user_repo.get_by_email(db, EMAIL) or user_repo.create(db, EMAIL, hash_password(PASSWORD))
    existing = {d.filename for d in doc_repo.list_for_user(db, user.id)}

    for sample in SAMPLES:
        if sample["filename"] in existing:
            print(f"  skipped {sample['filename']} (already there)")
            continue
        doc = ingest_document(db, user.id, sample["filename"], build_file(sample))
        if doc.status != "ready":
            print(f"  FAILED  {sample['filename']}: {doc.error_message}")
            doc_repo.delete_owned(db, doc)  # remove the broken record so a re-run can try again
            continue
        doc.reading_status = sample["reading_status"]
        doc_repo.save(db, doc)
        for note in sample["notes"]:
            note_repo.create(db, user.id, doc.id, note)
        add_demo_chats(db, user.id, doc, sample, rng)
        print(f"  added   {sample['filename']}")

    print(f"\nDemo account: {EMAIL} / {PASSWORD}")


if __name__ == "__main__":
    session = SessionLocal()
    try:
        seed(session)
    finally:
        session.close()
