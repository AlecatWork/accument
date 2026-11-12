"""The forms every request and response must fit (Pydantic models).

If someone sends the wrong shape (an email that isn't an email, a password that is too short), FastAPI rejects it automatically before the code even runs.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field



# ---------- accounts ----------


class SignupIn(BaseModel):
    """What someone sends to create an account."""
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)


class LoginIn(BaseModel):
    """What someone sends to log in."""
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    """The login wristband we hand back."""
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    """Public facts about a user (never the password)."""
    id: UUID
    email: str
    created_at: datetime

    model_config = {"from_attribute": True}


# ---------- papers ----------


class PaperOut(BaseModel):
    """One paper as shown in the library."""
    id: UUID
    filename: str
    title: str | None
    page_count: int | None
    status: str
    reading_status: str
    error_message: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}



class ReadingStatusIn(BaseModel):
    """Change the reader's bookmark on a paper."""

    reading_status: str = Field(pattern="^(to_read|reading|done)$")


# ---------- chat ----------


class AskIn(BaseModel):
    """A question about one paper (optionally continuing an existing chat)."""
    document_id: UUID
    question: str = Field(min_length=3, max_length=4000)
    conversation_id: UUID | None = None


class SourceOut(BaseModel):
    """One numbered excerpt the answer was based on."""
    n: int
    page: int
    snippet: str


class AskOut(BaseModel):
    """The finished answer."""
    conversation_id: UUID
    message_id: UUID
    answer: str
    sources: list[SourceOut]
    refused: bool = False


class FeedbackIn(BaseModel):
    """A thumbs up or down."""
    rating: str = Field(pattern="^(up|down)$")
    comment: str | None = None


class ConversationOut(BaseModel):
    """A chat thread in the history list."""

    id: UUID
    document_id: UUID
    title: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageOut(BaseModel):
    """One chat line."""

    id: UUID
    role: str
    content: str
    sources: list | dict | None
    rating: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------- compare + summaries ----------


class CompareIn(BaseModel):
    """Ask one question across 2-4 papers."""
    document_ids: list[UUID] = Field(min_length=2, max_length=4)
    question: str = Field(min_length=3, max_length=4000)



class CompareOut(BaseModel):
    """The comparison text."""

    answer: str


class SummaryIn(BaseModel):
    """Ask for a summary of a paper in a chosen style."""

    document_id: UUID
    kind: str = Field(default="short", pattern="^(short|key_points|simple)$")


class SummaryOut(BaseModel):
    """A saved summary."""

    id: UUID
    document_id: UUID
    kind: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------- notes ----------


class NoteIn(BaseModel):
    """A new note on a paper."""
    document_id: UUID
    content: str = Field(min_length=1, max_length=20000)


class NoteUpdate(BaseModel):
    """New text for an existing note."""

    content: str = Field(min_length=1, max_length=20000)



class NoteOut(BaseModel):
    """A note as shown on the Notes page."""
    id: UUID
    document_id: UUID
    content: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------- dashboard ----------

class NamedCount(BaseModel):
    """A label with a number, e.g. one bar in a bar chart."""

    name: str
    count: int


class DayCount(BaseModel):
    """Questions asked on one day."""

    day: str
    count: int


class RecentQuestion(BaseModel):
    """One of the latest questions, with enough info to jump back into that chat."""

    question: str
    paper_title: str
    document_id: UUID
    conversation_id: UUID
    asked_at: str


class StatsOut(BaseModel):
    """Everything the dashboard needs, in one response."""

    paper_count: int
    papers_this_week: int
    question_count: int
    questions_this_week: int
    note_count: int
    notes_this_week: int
    votes_up: int
    votes_down: int
    questions_by_day: list[DayCount]
    reading_status: dict[str, int]
    most_cited: list[NamedCount]
    notes_per_paper: list[NamedCount]
    recent_activity: list[RecentQuestion]


class HealthOut(BaseModel):
    """Is everything the app needs switched on?"""

    status: str
    app: str
    database: str
    tables: list[str]
    ollama: str
    chat_model: str
    chat_model_ready: bool
    embed_model: str
    embed_model_ready: bool



