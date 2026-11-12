"""Numbers for the dashboard: counts, trends and recent activity for one person."""

from datetime import timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.models import Conversation, Document, Feedback, Message, Note, QueryLog, utc_now

READING_STATES = ("to_read", "reading", "done")


def _count(db: Session, column, *conditions) -> int:
    """Count rows of a table that match the conditions."""
    return db.scalar(select(func.count(column)).where(*conditions)) or 0


def for_user(db: Session, user_id: UUID) -> dict:
    """Collect everything the dashboard shows. Cheap queries only: a person's data is small."""
    now = utc_now()
    week_ago = now - timedelta(days=7)
    window_start = now - timedelta(days=29)  # today + the 29 days before it = 30 bars

    # --- stat cards (total + "this week") ---
    paper_count = _count(db, Document.id, Document.user_id == user_id)
    papers_week = _count(db, Document.id, Document.user_id == user_id, Document.created_at >= week_ago)
    question_count = _count(db, QueryLog.id, QueryLog.user_id == user_id)
    questions_week = _count(db, QueryLog.id, QueryLog.user_id == user_id, QueryLog.created_at >= week_ago)
    note_count = _count(db, Note.id, Note.user_id == user_id)
    notes_week = _count(db, Note.id, Note.user_id == user_id, Note.created_at >= week_ago)

    vote_rows = db.execute(
        select(Feedback.rating, func.count()).where(Feedback.user_id == user_id).group_by(Feedback.rating)
    ).all()
    votes = {rating: total for rating, total in vote_rows}

    # --- questions per day, last 30 days (days with no questions show as 0) ---
    asked = db.scalars(
        select(QueryLog.created_at).where(QueryLog.user_id == user_id, QueryLog.created_at >= window_start)
    ).all()
    per_day: dict[str, int] = {}
    for stamp in asked:
        key = stamp.date().isoformat()
        per_day[key] = per_day.get(key, 0) + 1
    today = now.date()
    questions_by_day = [
        {"day": (day := (today - timedelta(days=offset)).isoformat()), "count": per_day.get(day, 0)}
        for offset in range(29, -1, -1)
    ]

    # --- reading status donut ---
    status_pairs = db.execute(
        select(Document.reading_status, func.count())
        .where(Document.user_id == user_id)
        .group_by(Document.reading_status)
    ).all()
    status_rows = {state: total for state, total in status_pairs}
    reading_status = {state: status_rows.get(state, 0) for state in READING_STATES}

    # --- most-cited papers: how many answers were actually built from each paper ---
    cited_rows = db.execute(
        select(Document.title, Document.filename, Message.sources)
        .join(Conversation, Conversation.document_id == Document.id)
        .join(Message, Message.conversation_id == Conversation.id)
        .where(Document.user_id == user_id, Message.role == "assistant")
    ).all()
    cited: dict[str, int] = {}
    for title, filename, sources in cited_rows:
        if sources:  # an empty list means the AI refused, so it doesn't count as "cited"
            name = title or filename
            cited[name] = cited.get(name, 0) + 1
    most_cited = [{"name": n, "count": c} for n, c in sorted(cited.items(), key=lambda kv: kv[1], reverse=True)[:8]]

    # --- notes per paper (papers with zero notes are included so the chart is honest) ---
    note_rows = db.execute(
        select(Document.title, Document.filename, func.count(Note.id))
        .outerjoin(Note, Note.document_id == Document.id)
        .where(Document.user_id == user_id)
        .group_by(Document.id)
    ).all()
    notes_per_paper = sorted(
        ({"name": t or f, "count": c} for t, f, c in note_rows), key=lambda row: row["count"], reverse=True
    )[:10]

    # --- recent activity: the last 5 questions, with ids so the dashboard can open that chat ---
    recent_rows = db.execute(
        select(Message, Conversation, Document)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .join(Document, Conversation.document_id == Document.id)
        .where(Conversation.user_id == user_id, Message.role == "user")
        .order_by(Message.created_at.desc())
        .limit(5)
    ).all()
    recent_activity = [
        {
            "question": msg.content,
            "paper_title": doc.title or doc.filename,
            "document_id": doc.id,
            "conversation_id": convo.id,
            "asked_at": msg.created_at.isoformat(),
        }
        for msg, convo, doc in recent_rows
    ]

    return {
        "paper_count": paper_count,
        "papers_this_week": papers_week,
        "question_count": question_count,
        "questions_this_week": questions_week,
        "note_count": note_count,
        "notes_this_week": notes_week,
        "votes_up": votes.get("up", 0),
        "votes_down": votes.get("down", 0),
        "questions_by_day": questions_by_day,
        "reading_status": reading_status,
        "most_cited": most_cited,
        "notes_per_paper": notes_per_paper,
        "recent_activity": recent_activity,
    }
