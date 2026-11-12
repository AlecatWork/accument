"""Smoke tests: every page opens without crashing, using a pretend backend.

Streamlit's AppTest runs a page's script without a browser. We replace the single function that
talks to the real backend (`api_client._request`) with one that returns canned answers.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

FRONTEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(FRONTEND))

import api_client  # noqa: E402

NOW = datetime.now(timezone.utc).isoformat()
PAPER = {
    "id": "11111111-1111-1111-1111-111111111111", "filename": "widgets.pdf", "title": "widgets",
    "page_count": 3, "status": "ready", "reading_status": "reading", "error_message": None, "created_at": NOW,
}  # fmt: skip
FAILED = {**PAPER, "id": "22222222-2222-2222-2222-222222222222", "title": "scan", "status": "failed",
          "error_message": "No readable text found."}  # fmt: skip
SECOND = {**PAPER, "id": "55555555-5555-5555-5555-555555555555", "title": "gadgets", "filename": "gadgets.md"}
NOTE = {"id": "33333333-3333-3333-3333-333333333333", "document_id": PAPER["id"], "content": "my note",
        "created_at": NOW, "updated_at": NOW}  # fmt: skip
CONVO = {"id": "44444444-4444-4444-4444-444444444444", "document_id": PAPER["id"], "title": "How many?", "created_at": NOW}
CONVO2 = {"id": "66666666-6666-6666-6666-666666666666", "document_id": PAPER["id"], "title": "Accuracy?", "created_at": NOW}
MESSAGES = [
    {"id": "m1", "role": "user", "content": "How many diagrams?", "sources": None, "created_at": NOW},
    {"id": "m2", "role": "assistant", "content": "500 [1].", "created_at": NOW, "rating": None,
     "sources": [{"n": 1, "page": 1, "snippet": "500 labeled diagrams"}]},
]  # fmt: skip
STATS = {
    "paper_count": 2, "papers_this_week": 1, "question_count": 3, "questions_this_week": 2,
    "note_count": 1, "notes_this_week": 1, "votes_up": 2, "votes_down": 1,
    "questions_by_day": [{"day": f"2026-11-{d:02d}", "count": d % 3} for d in range(1, 31)],
    "reading_status": {"to_read": 1, "reading": 1, "done": 0},
    "most_cited": [{"name": "widgets", "count": 3}],
    "notes_per_paper": [{"name": "widgets", "count": 1}, {"name": "scan", "count": 0}],
    "recent_activity": [{"question": "How many diagrams?", "paper_title": "widgets", "document_id": PAPER["id"],
                         "conversation_id": CONVO["id"], "asked_at": NOW}],
}  # fmt: skip
EMPTY_STATS = {**STATS, "paper_count": 0, "question_count": 0, "note_count": 0, "recent_activity": [],
               "most_cited": [], "notes_per_paper": []}  # fmt: skip
HEALTH = {"status": "ok", "app": "Accument", "database": "connected", "tables": [], "ollama": "connected",
          "chat_model": "llama3.2:3b", "chat_model_ready": True, "embed_model": "nomic-embed-text",
          "embed_model_ready": False}  # fmt: skip


@pytest.fixture(autouse=True)
def forget_cached_stats():
    """The dashboard remembers numbers for 60 seconds; tests must start with a clean memory."""
    st.cache_data.clear()


def fake_backend(stats=STATS, papers=(PAPER, SECOND, FAILED)):
    """Build a stand-in for api_client._request that answers by looking at the address asked for."""

    def fake(method, path, timeout=30, **kwargs):
        routes = {
            ("GET", "/stats"): stats, ("GET", "/papers"): list(papers), ("GET", "/health"): HEALTH,
            ("GET", "/auth/me"): {"email": "ada@example.com"}, ("GET", "/notes"): [NOTE],
            ("GET", "/chat/conversations"): [CONVO, CONVO2], ("GET", f"/chat/conversations/{CONVO['id']}"): MESSAGES,
            ("GET", f"/chat/conversations/{CONVO2['id']}"): MESSAGES,
            ("GET", "/summaries"): [{"id": "s1", "document_id": PAPER["id"], "kind": "short",
                                    "content": "A short summary.", "created_at": NOW}],
            ("POST", "/compare"): {"answer": "They differ."},
        }  # fmt: skip
        return routes.get((method, path), {"ok": True})

    return fake


def run(view: str, monkeypatch, backend=None) -> AppTest:
    monkeypatch.setattr(api_client, "_request", backend or fake_backend())
    app = AppTest.from_file(str(FRONTEND / view), default_timeout=20)
    app.session_state["token"] = "test-token"
    app.session_state["email"] = "ada@example.com"
    return app.run()


@pytest.mark.parametrize(
    "view", ["views/dashboard.py", "views/papers.py", "views/chat.py", "views/notes.py",
             "views/compare.py", "views/summaries.py", "views/settings.py"],
)  # fmt: skip
def test_every_page_opens_without_errors(view, monkeypatch):
    app = run(view, monkeypatch)
    assert not app.exception, [e.value for e in app.exception]


def test_dashboard_shows_four_cards_with_weekly_deltas(monkeypatch):
    app = run("views/dashboard.py", monkeypatch)
    assert [m.label for m in app.metric] == ["📄 Papers", "💬 Questions", "📝 Notes", "👍 Helpful answers"]
    assert app.metric[0].delta == "+1 this week"


def test_failed_paper_explains_why(monkeypatch):
    app = run("views/papers.py", monkeypatch)
    assert any("No readable text found." in e.value for e in app.error)


def test_notes_page_lists_notes_and_has_an_add_form(monkeypatch):
    app = run("views/notes.py", monkeypatch)
    assert any("my note" in m.value for m in app.markdown) or any("my note" in t.value for t in app.text_area)
    assert [b.label for b in app.button if "Add note" in b.label]


def test_chat_shows_history_with_thumbs(monkeypatch):
    monkeypatch.setattr(api_client, "_request", fake_backend())
    app = AppTest.from_file(str(FRONTEND / "views/chat.py"), default_timeout=20)
    app.session_state["token"] = "test-token"
    app.session_state["pending_paper"] = PAPER["id"]  # the notes-to-self the Dashboard leaves behind
    app.session_state["pending_convo"] = CONVO["id"]
    app.run()
    assert not app.exception
    labels = [b.label for b in app.button]
    assert "👍" in labels and "👎" in labels


def test_settings_tells_you_which_model_to_install(monkeypatch):
    app = run("views/settings.py", monkeypatch)
    assert any("ollama pull nomic-embed-text" in w.value for w in app.warning)


def run_home(monkeypatch, backend=None, logged_in=True) -> AppTest:
    monkeypatch.setattr(api_client, "_request", backend or fake_backend())
    app = AppTest.from_file(str(FRONTEND / "Home.py"), default_timeout=20)
    if logged_in:
        app.session_state["token"] = "test-token"
        app.session_state["email"] = "ada@example.com"
    return app.run()


def test_logged_out_visitors_only_see_the_login_page(monkeypatch):
    app = run_home(monkeypatch, logged_in=False)
    assert not app.exception
    assert app.title[0].value == "📄 Accument"
    assert not [b for b in app.sidebar.button]  # no log-out button when nobody is logged in


def test_logged_in_router_opens_the_dashboard_with_a_logout_button(monkeypatch):
    app = run_home(monkeypatch)
    assert not app.exception, [e.value for e in app.exception]
    assert app.title[0].value == "📊 Dashboard"
    assert [b.label for b in app.sidebar.button] == ["🚪 Log out"]


def test_logout_forgets_the_login(monkeypatch):
    app = run_home(monkeypatch)
    app.sidebar.button[0].click().run()
    assert "token" not in app.session_state
    assert app.title[0].value == "📄 Accument"


def test_new_user_sees_a_friendly_empty_dashboard_through_the_router(monkeypatch):
    app = run_home(monkeypatch, fake_backend(stats=EMPTY_STATS, papers=()))
    assert not app.exception, [e.value for e in app.exception]
    assert any("Upload your first paper" in i.value for i in app.info)


def open_chat_page(monkeypatch, calls: list):
    """Open the Chat page on the widgets paper, recording every request the page makes."""
    base = fake_backend()

    def recording(method, path, timeout=30, **kwargs):
        calls.append((method, path, kwargs.get("json")))
        return base(method, path, timeout, **kwargs)

    monkeypatch.setattr(api_client, "_request", recording)
    app = AppTest.from_file(str(FRONTEND / "views/chat.py"), default_timeout=20)
    app.session_state["token"] = "test-token"
    app.session_state["pending_paper"] = PAPER["id"]
    return app.run()


def test_picking_a_chat_from_the_history_dropdown_sticks(monkeypatch):
    """Regression: choosing a past chat used to snap straight back to "New chat"."""
    app = open_chat_page(monkeypatch, [])
    history = app.selectbox(key=f"chat_convo_{PAPER['id']}")
    history.select(CONVO2["id"]).run()
    assert not app.exception
    assert app.selectbox(key=f"chat_convo_{PAPER['id']}").value == CONVO2["id"]
    assert "👍" in [b.label for b in app.button]  # that chat's messages are on screen


def test_clicking_a_thumb_saves_the_vote_and_keeps_you_in_the_same_chat(monkeypatch):
    """Regression: clicking a thumb used to reset the page to "New chat"."""
    calls: list = []
    app = open_chat_page(monkeypatch, calls)
    key = f"chat_convo_{PAPER['id']}"
    app.selectbox(key=key).select(CONVO["id"]).run()
    app.button(key="up_m2").click().run()
    assert not app.exception
    assert app.selectbox(key=key).value == CONVO["id"]  # still in the same chat
    assert ("POST", "/chat/messages/m2/feedback", {"rating": "up"}) in calls  # and the vote was sent