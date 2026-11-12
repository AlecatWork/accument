"""Numbered sources and honest citations.

The AI is shown numbered excerpts [1], [2]... and told to put the number after each fact.
Small AIs sometimes invent numbers, so we delete any marker that doesn't match a real excerpt.
"""

import re

from app.core.models import Chunk

MARKER = re.compile(r"\[(\d+)\]")


def number_chunks(chunks: list[Chunk]) -> list[dict]:
    """Give each excerpt a number (starting at 1) and keep its page and a short preview."""
    sources = []
    for i, chunk in enumerate(chunks, start=1):
        sources.append(
            {
                "n": i,
                "page": chunk.page_number,
                "snippet": chunk.text[:280],
                "chunk_id": str(chunk.id),
            }
        )
    return sources


def keep_real_citations(answer: str, source_count: int) -> str:
    """Remove citation markers that point to excerpts that don't exist."""
    def repl(match: re.Match) -> str:
        n = int(match.group(1))
        return match.group(0) if 1 <= n <= source_count else ""
    
    return MARKER.sub(repl, answer).strip()



def used_pages(answer: str, sources: list[dict]) -> list[int]:
    """Which pages did the answer lean on? Falls back to the top 3 excerpts if no markers were used."""
    nums = {int(n) for n in MARKER.findall(answer)}
    pages = [s["page"] for s in sources if s["n"] in nums]
    if not pages:
        pages = [s["page"] for s in sources[:3]]
    return sorted(set(pages))