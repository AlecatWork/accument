"""Chatting with a paper, with answers that stream in word by word.

Two ways to ask:
  * POST /chat/ask         -> waits and returns the whole answer (simple, used by tests and the eval script)
  * POST /chat/ask/stream  -> sends the answer piece by piece (what the app uses; feels much faster)
"""

import json
from time import perf_counter
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.core import database
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.models import User
from app.core.rate_limit import limiter
from app.core.schemas import AskIn, AskOut, ConversationOut, FeedbackIn, MessageOut, SourceOut
from app.repositories import conversations as chat_repo
from app.repositories import documents as doc_repo
from app.services.llm.ollama import OllamaError, OllamaWriter
from app.services.rag import REFUSAL, answer_question, build_prompt, finalize_answer
from app.services.retriever import find_chunks

router = APIRouter()



def _begin_turn(db: Session, user: User, body: AskIn):
    """Shared first half of both ask endpoints.

    Checks the paper and chat belong to the user, saves their question, and searches the paper.
    Returns (conversation, paper, retrieved chunks, recent history, saved question, is_new_chat).
    """
    doc = doc_repo.get_owned(db, user.id, body.document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Paper not found")
    if doc.status != "ready":
        raise HTTPException(status_code=400, detail="This paper is not ready yet")

    is_new_chat = body.conversation_id is None
    if body.conversation_id:
        convo = chat_repo.get_owned(db, user.id, body.conversation_id)
        if not convo or convo.document_id != doc.id:
            raise HTTPException(status_code=404, detail="Chat not found")
    else:
        convo = chat_repo.create_conversation(db, user.id, doc.id, body.question[:80])

    history = [{"role": m.role, "content": m.content} for m in chat_repo.list_messages(db, convo.id)[-4:]]
    question_message = chat_repo.add_message(db, convo.id, "user", body.question)
    chunks = find_chunks(db, user.id, doc.id, body.question)
    return convo, doc, chunks, history, question_message.id, is_new_chat



@router.post("/ask", response_model=AskOut)
@limiter.limit(settings.chat_rate_limit)
def ask(request: Request, body: AskIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Ask a question and wait for the complete, cited answer."""
    convo, doc, chunks, history, question_id, is_new_chat = _begin_turn(db, user, body)

    started = perf_counter()
    usage: dict = {}
    try:
        answer, sources, refused = answer_question(body.question, chunks, history, usage)
    except OllamaError:
        chat_repo.discard_turn(db, convo.id, question_id, is_new_chat)  # don't keep an unanswered question
        raise
    elapsed = int((perf_counter() - started) * 1000)

    message = chat_repo.add_message(db, convo.id, "assistant", answer, sources)
    chat_repo.add_query_log(
        db,
        user_id=user.id,
        document_id=doc.id,
        question=body.question,
        answer=answer,
        retrieved_chunk_ids=[str(c.id) for c in chunks],
        latency_ms=elapsed,
        prompt_tokens=usage.get("prompt_tokens"),
        completion_tokens=usage.get("completion_tokens"),
    )
    return AskOut(
        conversation_id=convo.id,
        message_id=message.id,
        answer=answer,
        sources=[SourceOut(n=s["n"], page=s["page"], snippet=s["snippet"]) for s in sources],
        refused=refused,
    )



def _line(data: dict) -> str:
    """One event in the stream: a single line of JSON."""
    return json.dumps(data) + "\n"


@router.post("/ask/stream")
@limiter.limit(settings.chat_rate_limit)
def ask_stream(request: Request, body: AskIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Ask a question and receive the answer as it is written.

    The reply is a stream of JSON lines:
      {"type": "start", "conversation_id": ...}
      {"type": "token", "text": "..."}            (many of these)
      {"type": "done", "answer": ..., "sources": [...], "refused": false, "message_id": ..., "conversation_id": ...}
      {"type": "error", "detail": "..."}          (only if something went wrong)
    """
    convo, doc, chunks, history, question_id, is_new_chat = _begin_turn(db, user, body)

    # Grab plain values NOW. The database session closes when this function returns,
    # but the stream keeps running afterwards.
    convo_id, doc_id, user_id = convo.id, doc.id, user.id
    chunk_ids = [str(c.id) for c in chunks]
    question = body.question
    prompt, sources = build_prompt(question, chunks, history) if chunks else ("", [])

    def events():
        yield _line({"type": "start", "conversation_id": str(convo_id)})
        started = perf_counter()
        pieces: list[str] = []
        usage: dict = {}

        if chunks:
            try:
                for kind, value in OllamaWriter().stream(prompt):
                    if kind == "token":
                        pieces.append(value)
                        yield _line({"type": "token", "text": value})
                    else:
                        usage = value
            except OllamaError as exc:
                with database.SessionLocal() as session:  # don't keep an unanswered question
                    chat_repo.discard_turn(session, convo_id, question_id, is_new_chat)
                yield _line({"type": "error", "detail": str(exc)})
                return
            answer, final_sources, refused = finalize_answer("".join(pieces), sources)
        else:
            answer, final_sources, refused = REFUSAL, [], True
            yield _line({"type": "token", "text": REFUSAL})

        # Save the finished answer using a fresh session (the request's session is gone).
        with database.SessionLocal() as session:
            message = chat_repo.add_message(session, convo_id, "assistant", answer, final_sources)
            chat_repo.add_query_log(
                session,
                user_id=user_id,
                document_id=doc_id,
                question=question,
                answer=answer,
                retrieved_chunk_ids=chunk_ids,
                latency_ms=int((perf_counter() - started) * 1000),
                prompt_tokens=usage.get("prompt_tokens"),
                completion_tokens=usage.get("completion_tokens"),
            )
            message_id = message.id

        yield _line(
            {
                "type": "done",
                "answer": answer,
                "sources": [{"n": s["n"], "page": s["page"], "snippet": s["snippet"]} for s in final_sources],
                "refused": refused,
                "message_id": str(message_id),
                "conversation_id": str(convo_id),
            }
        )

    return StreamingResponse(events(), media_type="application/x-ndjson")



@router.get("/conversations", response_model=list[ConversationOut])
def list_convos(document_id: UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """The chat history for one paper."""
    return chat_repo.list_for_document(db, user.id, document_id)



@router.get("/conversations/{conversation_id}", response_model=list[MessageOut])
def get_messages(conversation_id: UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Every message of one chat."""
    convo = chat_repo.get_owned(db, user.id, conversation_id)
    if not convo:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat_repo.list_messages(db, convo.id)



@router.post("/messages/{message_id}/feedback")
def feedback(
    message_id: UUID, 
    body: FeedbackIn,
    user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Thumbs up or down on an answer. Voting again changes the vote."""
    message = chat_repo.get_owned_message(db, user.id, message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    chat_repo.upsert_feedback(db, message.id, user.id, body.rating, body.comment)
    return {"ok": True}