"""Every screen talks to the backend through here, so the web addresses and the login
wristband (token) are handled in exactly one place.
"""


import json
import os

import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")

CANT_REACH = f"Can't reach the backend at {BACKEND_URL}. Is it running? (docker compose logs backend)"


class ApiError(RuntimeError):
    """Something went wrong talking to the backend. The message is safe to show to the user."""


def _headers():
    """The login wristband, attached to every request (empty if nobody is logged in)."""
    token = st.session_state.get("token")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def _handle(res: requests.Response):
    """Turn a backend reply into data, or into a clear ApiError."""
    if res.status_code == 401:
        st.session_state.pop("token", None)
        st.session_state.pop("email", None)
        raise ApiError("Please log in again")
    if not res.ok:
        try:
            detail = res.json().get("detail", res.text)
        except ValueError:
            detail = res.text
        if isinstance(detail, list) and detail:
            detail = detail[0].get("msg", str(detail[0]))
        raise ApiError(str(detail))
    return res.json() if res.content else None


def _request(method: str, path: str, timeout: float = 30, **kwargs):
    """Send one request to the backend and return the data."""
    try:
        res = requests.request(method, f"{BACKEND_URL}{path}", headers=_headers(), timeout=timeout, **kwargs)
    except requests.exceptions.RequestException as exc:
        raise ApiError(CANT_REACH) from exc
    return _handle(res)


# ---------- accounts ----------

def signup(email: str, password: str):
    return _request("POST", "/auth/signup", json={"email": email, "password": password})


def login(email: str, password: str):
    return _request("POST", "/auth/login", json={"email": email, "password": password})


def me():
    return _request("GET", "/auth/me")


def health():
    """Backend + Ollama status. No login needed."""
    return _request("GET", "/health", timeout=8)



# ---------- papers ----------
def list_papers():
    return _request("GET", "/papers")


def upload_paper(file_name: str, file_bytes: bytes):
    """Upload one file. Reading it can take minutes on a laptop, so we wait up to 10 minutes."""
    return _request("POST", "/papers", timeout=600, files={"file": (file_name, file_bytes)})


def delete_paper(paper_id: str):
    return _request("DELETE", f"/papers/{paper_id}")


def set_reading_status(paper_id: str, reading_status: str):
    return _request("PATCH", f"/papers/{paper_id}", json={"reading_status": reading_status})




# ---------- chat ----------

def stream_ask(document_id: str, question: str, conversation_id: str | None, meta: dict):
    """Ask a question and yield the answer piece by piece, like watching someone type.

    `meta` is filled in as we go (conversation id, final cleaned answer, sources...).
    """
    body = {"document_id": document_id, "question": question, "conversation_id": conversation_id}
    try:
        res = requests.post(
            f"{BACKEND_URL}/chat/ask/stream", headers=_headers(), json=body, stream=True, timeout=(5, 600)
        )
    except requests.exceptions.RequestException as exc:
        raise ApiError(CANT_REACH) from exc
    with res:
        if not res.ok:
            _handle(res)  # raises a friendly ApiError
        res.encoding = "utf-8"
        for line in res.iter_lines(decode_unicode=True):
            if not line:
                continue
            event = json.loads(line)
            if event["type"] == "start":
                meta["conversation_id"] = event["conversation_id"]
            elif event["type"] == "token":
                yield event["text"]
            elif event["type"] == "done":
                meta.update(event)
            elif event["type"] == "error":
                raise ApiError(event["detail"])


def list_conversations(document_id: str):
    return _request("GET", "/chat/conversations", params={"document_id": document_id})


def list_messages(conversation_id: str):
    return _request("GET", f"/chat/conversations/{conversation_id}")


def send_feedback(message_id: str, rating: str):
    return _request("POST", f"/chat/messages/{message_id}/feedback", json={"rating": rating})



# ---------- compare + summaries ----------

def compare(document_ids: list[str], question: str):
    return _request("POST", "/compare", timeout=600, json={"document_ids": document_ids, "question": question})


def create_summary(document_id: str, kind: str = "short"):
    return _request("POST", "/summaries", timeout=600, json={"document_id": document_id, "kind": kind})


def list_summaries(document_id: str):
    return _request("GET", "/summaries", params={"document_id": document_id})



# ---------- notes ----------

def create_note(document_id: str, content: str):
    return _request("POST", "/notes", json={"document_id": document_id, "content": content})


def list_notes(document_id: str):
    return _request("GET", "/notes", params={"document_id": document_id})


def edit_note(note_id: str, content: str):
    return _request("PUT", f"/notes/{note_id}", json={"content": content})


def delete_note(note_id: str):
    return _request("DELETE", f"/notes/{note_id}")




# ---------- dashboard ----------

def get_stats():
    return _request("GET", "/stats")