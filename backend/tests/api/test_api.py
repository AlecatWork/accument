"""End-to-end tests of the API: real endpoints, real (tiny) database, fake AI."""

import json

from tests.conftest import WIDGET_TEXT


def _stream_events(response) -> list[dict]:
    """Parse a streamed reply (one JSON event per line)."""
    return [json.loads(line) for line in response.text.splitlines() if line.strip()]


# ---------- accounts ----------


def test_signup_login_and_me(client):
    signup = client.post("/auth/signup", json={"email": "Ada@Example.com", "password": "password123"})
    assert signup.status_code == 200
    login = client.post("/auth/login", json={"email": "ada@example.com", "password": "password123"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert client.get("/auth/me", headers=headers).json()["email"] == "ada@example.com"


def test_wrong_password_and_duplicate_email(client, auth):
    bad = client.post("/auth/login", json={"email": "ada@example.com", "password": "nope-nope-nope"})
    assert bad.status_code == 401
    again = client.post("/auth/signup", json={"email": "ada@example.com", "password": "password123"})
    assert again.status_code == 400


def test_protected_endpoints_need_a_login(client):
    assert client.get("/papers").status_code == 401
    assert client.get("/papers", headers={"Authorization": "Bearer nonsense"}).status_code == 401


# ---------- papers ----------


def test_upload_makes_a_ready_paper_and_rejects_unknown_types(client, auth, fake_ai, paper):
    assert paper["status"] == "ready" and paper["reading_status"] == "to_read" and paper["page_count"] == 1
    bad = client.post("/papers", headers=auth, files={"file": ("pic.png", b"x", "image/png")})
    assert bad.status_code == 400 and "Unsupported" in bad.json()["detail"]
    empty = client.post("/papers", headers=auth, files={"file": ("e.txt", b"", "text/plain")})
    assert empty.status_code == 400


def test_failed_processing_explains_why(client, auth, fake_ai):
    scanned = client.post("/papers", headers=auth, files={"file": ("blank.txt", b"   \n\n  ", "text/plain")})
    assert scanned.json()["status"] == "failed"
    assert "No readable text" in scanned.json()["error_message"]


def test_people_cannot_see_each_others_papers(client, auth, paper):
    other = client.post("/auth/signup", json={"email": "bob@example.com", "password": "password123"})
    bob = {"Authorization": f"Bearer {other.json()['access_token']}"}
    assert client.get("/papers", headers=bob).json() == []
    assert client.get(f"/papers/{paper['id']}", headers=bob).status_code == 404
    assert client.delete(f"/papers/{paper['id']}", headers=bob).status_code == 404


def test_reading_status_can_be_changed(client, auth, paper):
    done = client.patch(f"/papers/{paper['id']}", headers=auth, json={"reading_status": "done"})
    assert done.json()["reading_status"] == "done"
    bad = client.patch(f"/papers/{paper['id']}", headers=auth, json={"reading_status": "finished-ish"})
    assert bad.status_code == 422


def test_deleting_a_paper_removes_its_notes_and_chats(client, auth, paper):
    client.post("/notes", headers=auth, json={"document_id": paper["id"], "content": "remember this"})
    client.post("/chat/ask", headers=auth, json={"document_id": paper["id"], "question": "How many diagrams?"})
    assert client.delete(f"/papers/{paper['id']}", headers=auth).json() == {"ok": True}
    assert client.get("/papers", headers=auth).json() == []
    assert client.get("/stats", headers=auth).json()["note_count"] == 0


# ---------- chat ----------


def test_ask_returns_a_cited_answer_and_logs_it(client, auth, paper, fake_ai):
    reply = client.post("/chat/ask", headers=auth, json={"document_id": paper["id"], "question": "How many diagrams?"})
    body = reply.json()
    assert reply.status_code == 200 and not body["refused"]
    assert "[1]" in body["answer"] and body["sources"][0]["page"] == 1
    messages = client.get(f"/chat/conversations/{body['conversation_id']}", headers=auth).json()
    assert [m["role"] for m in messages] == ["user", "assistant"]
    assert "Widget" in fake_ai.prompts[-1]  # the real excerpt reached the AI


def test_invented_citations_are_removed(client, auth, paper, fake_ai):
    fake_ai.reply = "It uses 500 diagrams [1] and flies to Mars [7]."
    body = client.post(
        "/chat/ask", headers=auth, json={"document_id": paper["id"], "question": "How many diagrams?"}
    ).json()
    assert "[7]" not in body["answer"] and "[1]" in body["answer"]


def test_ai_refusal_has_no_sources(client, auth, paper, fake_ai):
    fake_ai.reply = "I can't find that in the paper."
    body = client.post(
        "/chat/ask", headers=auth, json={"document_id": paper["id"], "question": "Mars colonies?"}
    ).json()
    assert body["refused"] and body["sources"] == []


def test_ollama_down_gives_a_friendly_503(client, auth, paper, fake_ai):
    fake_ai.broken = True
    reply = client.post("/chat/ask", headers=auth, json={"document_id": paper["id"], "question": "How many diagrams?"})
    assert reply.status_code == 503 and "Ollama" in reply.json()["detail"]


def test_streaming_sends_tokens_then_a_final_event(client, auth, paper, fake_ai):
    reply = client.post(
        "/chat/ask/stream", headers=auth, json={"document_id": paper["id"], "question": "How many diagrams?"}
    )
    events = _stream_events(reply)
    kinds = [e["type"] for e in events]
    assert kinds[0] == "start" and kinds[-1] == "done" and kinds.count("token") >= 3
    done = events[-1]
    assert done["answer"] == fake_ai.reply and done["sources"][0]["page"] == 1
    # the streamed answer was saved, so it shows up in the chat history
    history = client.get(f"/chat/conversations/{done['conversation_id']}", headers=auth).json()
    assert history[-1]["content"] == fake_ai.reply


def test_streaming_reports_ollama_errors_as_an_event(client, auth, paper, fake_ai):
    fake_ai.broken = True
    reply = client.post(
        "/chat/ask/stream", headers=auth, json={"document_id": paper["id"], "question": "How many diagrams?"}
    )
    events = _stream_events(reply)
    assert events[-1]["type"] == "error" and "Ollama" in events[-1]["detail"]


def test_failed_questions_leave_no_unanswered_chat_behind(client, auth, paper, fake_ai):
    fake_ai.broken = True
    ask = {"document_id": paper["id"], "question": "How many diagrams?"}
    assert client.post("/chat/ask", headers=auth, json=ask).status_code == 503
    client.post("/chat/ask/stream", headers=auth, json=ask)
    assert client.get("/chat/conversations", headers=auth, params={"document_id": paper["id"]}).json() == []

    # and in an existing chat, only the failed question disappears
    fake_ai.broken = False
    first = client.post("/chat/ask", headers=auth, json=ask).json()
    fake_ai.broken = True
    again = {**ask, "conversation_id": first["conversation_id"], "question": "And accuracy?"}
    assert client.post("/chat/ask", headers=auth, json=again).status_code == 503
    messages = client.get(f"/chat/conversations/{first['conversation_id']}", headers=auth).json()
    assert [m["content"] for m in messages if m["role"] == "user"] == ["How many diagrams?"]


def test_follow_up_questions_carry_history(client, auth, paper, fake_ai):
    first = client.post(
        "/chat/ask", headers=auth, json={"document_id": paper["id"], "question": "How many diagrams?"}
    ).json()
    client.post(
        "/chat/ask",
        headers=auth,
        json={"document_id": paper["id"], "question": "And the accuracy?", "conversation_id": first["conversation_id"]},
    )
    assert "How many diagrams?" in fake_ai.prompts[-1]


def test_one_thumb_per_answer_but_you_can_change_your_mind(client, auth, paper, fake_ai):
    body = client.post(
        "/chat/ask", headers=auth, json={"document_id": paper["id"], "question": "How many diagrams?"}
    ).json()
    url = f"/chat/messages/{body['message_id']}/feedback"
    assert client.post(url, headers=auth, json={"rating": "up"}).json() == {"ok": True}
    assert client.post(url, headers=auth, json={"rating": "down"}).json() == {"ok": True}
    stats = client.get("/stats", headers=auth).json()
    assert (stats["votes_up"], stats["votes_down"]) == (0, 1)


# ---------- notes ----------


def test_a_paper_can_have_many_notes_that_can_be_edited_and_deleted(client, auth, paper):
    doc = paper["id"]
    first = client.post("/notes", headers=auth, json={"document_id": doc, "content": "first"}).json()
    client.post("/notes", headers=auth, json={"document_id": doc, "content": "second"})
    assert len(client.get("/notes", headers=auth, params={"document_id": doc}).json()) == 2

    edited = client.put(f"/notes/{first['id']}", headers=auth, json={"content": "first (edited)"})
    assert edited.json()["content"] == "first (edited)"
    assert client.delete(f"/notes/{first['id']}", headers=auth).json() == {"ok": True}
    remaining = client.get("/notes", headers=auth, params={"document_id": doc}).json()
    assert [n["content"] for n in remaining] == ["second"]


def test_notes_are_private(client, auth, paper):
    note = client.post("/notes", headers=auth, json={"document_id": paper["id"], "content": "mine"}).json()
    other = client.post("/auth/signup", json={"email": "bob@example.com", "password": "password123"})
    bob = {"Authorization": f"Bearer {other.json()['access_token']}"}
    assert client.put(f"/notes/{note['id']}", headers=bob, json={"content": "hacked"}).status_code == 404
    assert client.delete(f"/notes/{note['id']}", headers=bob).status_code == 404


# ---------- summaries + compare ----------


def test_summary_is_saved_and_listed(client, auth, paper, fake_ai):
    fake_ai.reply = "Widgets learn from 500 diagrams."
    made = client.post("/summaries", headers=auth, json={"document_id": paper["id"], "kind": "short"})
    assert made.status_code == 200 and made.json()["content"] == fake_ai.reply
    listed = client.get("/summaries", headers=auth, params={"document_id": paper["id"]}).json()
    assert len(listed) == 1 and listed[0]["kind"] == "short"
    assert client.post("/summaries", headers=auth, json={"document_id": paper["id"], "kind": "poem"}).status_code == 422


def test_compare_needs_two_ready_papers(client, auth, paper, fake_ai):
    other = client.post("/papers", headers=auth, files={"file": ("gadgets.md", WIDGET_TEXT, "text/markdown")}).json()
    fake_ai.reply = "Both papers use diagrams."
    ok = client.post("/compare", headers=auth, json={"document_ids": [paper["id"], other["id"]], "question": "Data?"})
    assert ok.status_code == 200 and ok.json()["answer"] == fake_ai.reply
    one = client.post("/compare", headers=auth, json={"document_ids": [paper["id"]], "question": "Data?"})
    assert one.status_code == 422


# ---------- dashboard ----------


def test_dashboard_numbers(client, auth, paper, fake_ai):
    client.patch(f"/papers/{paper['id']}", headers=auth, json={"reading_status": "reading"})
    client.post("/notes", headers=auth, json={"document_id": paper["id"], "content": "a note"})
    client.post("/chat/ask", headers=auth, json={"document_id": paper["id"], "question": "How many diagrams?"})

    stats = client.get("/stats", headers=auth).json()
    assert stats["paper_count"] == 1 and stats["papers_this_week"] == 1
    assert stats["question_count"] == 1 and stats["questions_this_week"] == 1
    assert stats["note_count"] == 1 and stats["notes_this_week"] == 1
    assert stats["reading_status"] == {"to_read": 0, "reading": 1, "done": 0}
    assert len(stats["questions_by_day"]) == 30 and stats["questions_by_day"][-1]["count"] == 1
    assert stats["most_cited"] == [{"name": "widgets", "count": 1}]
    assert stats["notes_per_paper"] == [{"name": "widgets", "count": 1}]
    assert stats["recent_activity"][0]["question"] == "How many diagrams?"
    assert stats["recent_activity"][0]["conversation_id"]


def test_empty_dashboard_for_a_new_user(client, auth):
    stats = client.get("/stats", headers=auth).json()
    assert stats["paper_count"] == 0 and stats["recent_activity"] == [] and stats["most_cited"] == []
    assert len(stats["questions_by_day"]) == 30
