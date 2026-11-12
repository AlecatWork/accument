"""RAG system

1. Find the relevant excerpts (done in retriever.py).
2. Put them in the prompt as numbered excerpts and tell the AI to answer ONLY from them.
3. Clean up the reply so it only cites excerpts that really exist.
"""


from app.core.models import Chunk
from app.services.citations import keep_real_citations, number_chunks
from app.services.llm.ollama import OllamaWriter

REFUSAL = "I can't find that in the paper."

SYSTEM = """You are Accument, a reading helper for research papers.
Answer ONLY using the numbered excerpts.
Put a marker like [1] after each fact.
If the excerpts do not contain the answer, reply exactly: I can't find that in the paper.
Do not invent page numbers, authors, or numbers."""


def build_prompt(
    question: str, chunks: list[Chunk], history: list[dict] | None = None
) -> tuple[str, list[dict]]:
    """Write the full instructions the AI will see. Returns (prompt text, numbered sources)."""
    sources = number_chunks(chunks)
    excerpts = [f"[{s['n']}] (Page {s['page']}): {chunk.text}" for s, chunk in zip(sources, chunks)]

    # A little recent chat history lets follow-ups like "and the limitations?" make sense.
    recent = ""
    if history:
        lines = [f"{m['role'].capitalize()}: {m['content'][:300]}" for m in history[-4:]]
        recent = "Earlier in this chat:\n" + "\n".join(lines) + "\n\n"

    prompt = (
        f"{SYSTEM}\n\nExcerpts:\n" + "\n\n".join(excerpts) + f"\n\n{recent}Question: {question}\nAnswer:"
    )
    return prompt, sources


def finalize_answer(raw: str, sources: list[dict]) -> tuple[str, list[dict], bool]:
    """Turn the AI's raw reply into (clean answer, sources to show, was it a refusal?)."""
    if not raw or REFUSAL.lower() in raw.lower():
        return REFUSAL, [], True
    return keep_real_citations(raw, len(sources)), sources, False


def answer_question(
    question: str, chunks: list[Chunk], history: list[dict] | None = None, usage: dict | None = None
) -> tuple[str, list[dict], bool]:
    """Answer in one go (the non-streaming path). Fills `usage` with token counts if you pass a dict."""
    if not chunks: 
        return REFUSAL, [], True
    prompt, sources = build_prompt(question, chunks, history)
    result = OllamaWriter().generate(prompt)
    if usage is not None:
        usage.update(prompt_tokens=result.prompt_tokens, completion_tokens=result.completion_tokens)
    return finalize_answer(result.text, sources)
