"""Talking to Ollama, the program on my Mac that runs the AI models.

Two jobs:
  1. WRITING answers (the chat model, e.g. llama3.2:3b)
  2. EMBEDDING text: turning a sentence into a list of numbers that captures its meaning,
     so we can later find passages that mean the same thing as a question.
"""

import json
from collections.abc import Iterator

import httpx

from app.config import settings
from app.core.logging import logger
from app.services.llm.base import Generation, Writer


class OllamaError(Exception):
    """Ollama is switched off, the model isn't installed, or something else went wrong.

    The message is written in plain English so it can be shown straight to the user.
    """


def _explain(exc: Exception, model: str) -> str:
    """Turn a technical network error into a sentence a human can act on."""
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 404:
        return f"Ollama doesn't have the model '{model}'. On your Mac, run: ollama pull {model}"
    if isinstance(exc, httpx.ConnectError):
        return f"Can't reach Ollama at {settings.ollama_url}. Open the Ollama app on your Mac and try again."
    if isinstance(exc, httpx.TimeoutException):
        return "Ollama took too long to answer. The model may still be waking up; try again in a minute."
    return f"Ollama problem: {exc}"


def _timeout() -> httpx.Timeout:
    """Be patient when reading (old laptops are slow), but fail fast if Ollama isn't there."""
    return httpx.Timeout(settings.ollama_timeout, connect=5)


class OllamaWriter(Writer):
    """Writes answers with the chat model that runs in Ollama."""

    def _body(self, prompt: str, stream: bool) -> dict:
        """The request we send. Low temperature = sticks to the facts instead of getting creative."""
        return {
            "model": settings.model_name,
            "prompt": prompt,
            "stream": stream,
            "options": {"temperature": 0.2, "num_ctx": settings.num_ctx},
        }

    def generate(self, prompt: str) -> Generation:
        """Ask for a complete answer and wait for it."""
        try:
            reply = httpx.post(
                f"{settings.ollama_url}/api/generate", json=self._body(prompt, False), timeout=_timeout()
            )
            reply.raise_for_status()
            data = reply.json()
        except httpx.HTTPError as exc:
            logger.info("Writer failed: %s", exc)
            raise OllamaError(_explain(exc, settings.model_name)) from exc
        return Generation(
            text=(data.get("response") or "").strip(),
            prompt_tokens=data.get("prompt_eval_count"),
            completion_tokens=data.get("eval_count"),
        )

    def stream(self, prompt: str) -> Iterator[tuple[str, object]]:
        """Ask for an answer and receive it word by word, like watching someone type."""
        try:
            with httpx.stream(
                "POST", f"{settings.ollama_url}/api/generate", json=self._body(prompt, True), timeout=_timeout()
            ) as reply:
                reply.raise_for_status()
                for line in reply.iter_lines():
                    if not line:
                        continue
                    data = json.loads(line)
                    if data.get("response"):
                        yield "token", data["response"]
                    if data.get("done"):
                        yield "usage", {
                            "prompt_tokens": data.get("prompt_eval_count"),
                            "completion_tokens": data.get("eval_count"),
                        }
                        break
        except httpx.HTTPError as exc:
            logger.info("Streaming writer failed: %s", exc)
            raise OllamaError(_explain(exc, settings.model_name)) from exc


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Turn each text into its "meaning numbers" (one list of numbers per text)."""
    vectors = []
    for text in texts:
        try:
            reply = httpx.post(
                f"{settings.ollama_url}/api/embeddings",
                json={"model": settings.embed_model, "prompt": text},
                timeout=_timeout(),
            )
            reply.raise_for_status()
        except httpx.HTTPError as exc:
            raise OllamaError(_explain(exc, settings.embed_model)) from exc
        vectors.append(reply.json()["embedding"])
    return vectors


def embed_one(text: str) -> list[float]:
    """Turn a single text (usually the user's question) into meaning numbers."""
    return embed_texts([text])[0]
