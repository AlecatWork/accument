"""The front door of the backend: creates the app and plugs in every set of endpoints."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api import auth, chat, compare, health, notes, papers, stats, summaries
from app.config import settings
from app.core.rate_limit import limiter
from app.services.llm.ollama import OllamaError


app = FastAPI(title=settings.app_name, version="0.2.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(OllamaError)
async def ollama_problem(_request: Request, exc: OllamaError):
    """Whenever Ollama is off or missing a model, answer "503 Service Unavailable" with a helpful message."""
    return JSONResponse(status_code=503, content={"detail": str(exc)})



app.include_router(health.router)
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(papers.router, prefix="/papers", tags=["papers"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(compare.router, prefix="/compare", tags=["compare"])
app.include_router(summaries.router, prefix="/summaries", tags=["summaries"])
app.include_router(notes.router, prefix="/notes", tags=["notes"])
app.include_router(stats.router, prefix="/stats", tags=["stats"])



