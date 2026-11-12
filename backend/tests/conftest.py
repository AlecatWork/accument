"""Shared test setup.

Tests never touch the real Postgres database or the real AI. Instead they use:
  * a tiny throw-away SQLite database (in memory, wiped before every test)
  * a "fake AI" that returns fixed answers, so tests are fast and predictable
"""

import os
import tempfile

# These must be set BEFORE the app is imported, because settings are read at import time.
os.environ["UPLOAD_DIR"] = tempfile.mkdtemp()
os.environ["CHROMA_PATH"] = tempfile.mkdtemp()
os.environ["JWT_SECRET"] = "test-secret"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core import database  # noqa: E402
from app.core.models import Base  # noqa: E402
from app.core.rate_limit import limiter  # noqa: E402
from app.main import app  # noqa: E402
from app.services.llm.base import Generation  # noqa: E402
from app.services.llm.ollama import OllamaError, OllamaWriter  # noqa: E402

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)


@event.listens_for(engine, "connect")
def _turn_on_foreign_keys(dbapi_connection, _record):
    """SQLite ignores "delete children with the parent" unless we ask it to obey."""
    dbapi_connection.execute("PRAGMA foreign_keys=ON")


TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture(autouse=True)
def fresh_database(monkeypatch):
    """Before every test: empty tables, and point the app at the test database."""
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(database, "SessionLocal", TestingSession)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[database.get_db] = override_get_db
    limiter.enabled = False  # the speed limit would get in the way of rapid-fire tests
    yield
    app.dependency_overrides.clear()


class FakeAI:
    """Remembers what we told it to say, and what it was asked."""

    reply = "Widgets use 500 labeled diagrams [1]."
    broken = False
    prompts: list[str] = []


@pytest.fixture
def fake_ai(monkeypatch):
    """Replace Ollama (the writer and the embedder) with instant, predictable stand-ins."""
    FakeAI.reply = "Widgets use 500 labeled diagrams [1]."
    FakeAI.broken = False
    FakeAI.prompts = []

    def fake_generate(self, prompt):
        FakeAI.prompts.append(prompt)
        if FakeAI.broken:
            raise OllamaError("Can't reach Ollama. Open the Ollama app and try again.")
        return Generation(text=FakeAI.reply, prompt_tokens=12, completion_tokens=7)

    def fake_stream(self, prompt):
        FakeAI.prompts.append(prompt)
        if FakeAI.broken:
            raise OllamaError("Can't reach Ollama. Open the Ollama app and try again.")
        for word in FakeAI.reply.split(" "):
            yield "token", word + " "
        yield "usage", {"prompt_tokens": 12, "completion_tokens": 7}

    def no_meaning_search(_text):
        raise OllamaError("embedding model unavailable in tests")  # retriever falls back to keywords

    monkeypatch.setattr(OllamaWriter, "generate", fake_generate)
    monkeypatch.setattr(OllamaWriter, "stream", fake_stream)
    monkeypatch.setattr("app.services.ingestion.embed_texts", lambda texts: [[0.0, 0.0, 0.0] for _ in texts])
    monkeypatch.setattr("app.services.embeddings.add_chunks", lambda **kwargs: None)
    monkeypatch.setattr("app.services.embeddings.delete_document", lambda document_id: None)
    monkeypatch.setattr("app.api.papers.delete_document", lambda document_id: None)
    monkeypatch.setattr("app.services.retriever.embed_one", no_meaning_search)
    return FakeAI


@pytest.fixture
def client():
    """A browser stand-in that talks to the app directly."""
    return TestClient(app)


@pytest.fixture
def auth(client):
    """Sign up a user and return the headers that prove who they are."""
    reply = client.post("/auth/signup", json={"email": "ada@example.com", "password": "password123"})
    return {"Authorization": f"Bearer {reply.json()['access_token']}"}


WIDGET_TEXT = (
    b"Widget Learning for Small Labs\n\nAuthor: Ada Example. Year: 2024.\n\n"
    b"A widget is trained on 500 labeled diagrams so a small lab can classify captions.\n\n"
    b"Accuracy is 91.5% on the test set. The only limitation is that it works on English captions."
)


@pytest.fixture
def paper(client, auth, fake_ai):
    """Upload a small text paper and return its JSON."""
    reply = client.post("/papers", headers=auth, files={"file": ("widgets.txt", WIDGET_TEXT, "text/plain")})
    assert reply.status_code == 200, reply.text
    return reply.json()
