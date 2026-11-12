"""A "is everything switched on?" check, used by Docker and by the Settings page."""

import httpx
from fastapi import APIRouter
from sqlalchemy import text

from app.config import settings
from app.core.database import engine
from app.core.schemas import HealthOut

router = APIRouter(tags=["health"])


def _has_model(installed: list[str], wanted: str) -> bool:
    """Is `wanted` installed? "nomic-embed-text" matches "nomic-embed-text:latest"."""
    if ":" in wanted:
        return wanted in installed
    return wanted in installed or f"{wanted}:latest" in installed


@router.get("/health", response_model=HealthOut)
def health():
    """Check the database and Ollama (and whether the two AI models we need are installed)."""
    installed: list[str] = []
    try:
        reply = httpx.get(f"{settings.ollama_url}/api/tags", timeout=3)
        if reply.status_code == 200:
            ollama = "connected"
            installed = [m.get("name", "") for m in reply.json().get("models", [])]
        else:
            ollama = "error"
    except httpx.HTTPError:
        ollama = "not reachable"

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            rows = conn.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename")
            )
            tables = [row[0] for row in rows]
        database = "connected"
    except Exception:
        database = "not reachable"
        tables = []

    return HealthOut(
        status="ok" if database == "connected" else "degraded",
        app=settings.app_name,
        database=database,
        tables=tables,
        ollama=ollama,
        chat_model=settings.model_name,
        chat_model_ready=_has_model(installed, settings.model_name),
        embed_model=settings.embed_model,
        embed_model_ready=_has_model(installed, settings.embed_model),
    )
