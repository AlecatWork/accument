"""Database helpers for chats: conversations, messages, thumbs and the question diary."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.models import Conversation, Feedback, Message, QueryLog


def create_conversation(db: Session, user_id: UUID, document_id: UUID, title: str | None) -> Conversation:
    """Start a new chat thread."""
    row = Conversation(user_id=user_id, document_id=document_id, title=title)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_owned(db: Session, user_id: UUID, conversation_id: UUID) -> Conversation | None:
    """One chat thread, but only if it belongs to this person."""
    return db.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id, Conversation.user_id == user_id
        )
    )


def list_for_document(db: Session, user_id: UUID, document_id: UUID) -> list[Conversation]:
    """A person's chat threads about one paper, most recent first."""
    return list(
        db.scalars(
            select(Conversation)
            .where(Conversation.user_id == user_id, Conversation.document_id == document_id)
            .order_by(Conversation.updated_at.desc())
        ).all()
    )


def add_message(db: Session, conversation_id: UUID, role: str, content: str, sources=None) -> Message:
    """Save one line of a chat."""
    row = Message(conversation_id=conversation_id, role=role, content=content, sources=sources)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_messages(db: Session, conversation_id: UUID) -> list[Message]:
    """All lines of a chat, oldest first."""
    return list(
        db.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .options(selectinload(Message.feedback))
            .order_by(Message.created_at)
        ).all()
    )
 


def get_owned_message(db: Session, user_id: UUID, message_id: UUID) -> Message | None:
    """One message, but only if its chat belongs to this person."""
    return db.scalar(
        select(Message).join(Conversation).where(Message.id == message_id, Conversation.user_id == user_id)
    )


def upsert_feedback(db: Session, message_id: UUID, user_id: UUID, rating: str, comment: str | None) -> Feedback:
    """Save a thumbs vote. Voting again on the same answer changes the vote instead of adding a second."""
    existing = db.scalar(select(Feedback).where(Feedback.message_id == message_id))
    if existing:
        existing.rating = rating
        existing.comment = comment
        db.commit()
        db.refresh(existing)
        return existing
    row = Feedback(message_id=message_id, user_id=user_id, rating=rating, comment=comment)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def add_query_log(db: Session, **kwargs) -> QueryLog:
    """Write a diary entry for one question (speed, tokens, which excerpts were used)."""
    row = QueryLog(**kwargs)
    db.add(row)
    db.commit()
    return row


def discard_turn(db: Session, conversation_id: UUID, message_id: UUID, delete_conversation: bool) -> None:
    """Undo a question that never got an answer (for example because Ollama was off).

    Removes the lonely question, and the whole chat too if that question was what started it,
    so failed attempts don't clutter the chat history.
    """
    if delete_conversation:
        convo = db.get(Conversation, conversation_id)
        if convo:
            db.delete(convo)  # the database also removes the chat's messages
    else:
        message = db.get(Message, message_id)
        if message:
            db.delete(message)
    db.commit()
