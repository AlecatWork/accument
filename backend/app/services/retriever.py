"""Finding the right excerpts for a question: "hybrid search".

Two searchers work side by side:
  * MEANING search (ChromaDB): finds passages that mean the same thing, even with different words.
  * KEYWORD search (BM25): finds passages that contain the exact words (great for names and numbers).
Their ranked lists are then merged with "Reciprocal Rank Fusion" (RRF): a passage that ranks
well on BOTH lists wins, like a restaurant that two different friends both recommend.
"""

import math
import re
from uuid import UUID

from rank_bm25 import BM25Okapi
from sqlalchemy.orm import Session

from app.config import settings
from app.core.models import Chunk
from app.repositories import chunks as chunk_repo
from app.services.embeddings import get_collection
from app.services.llm.ollama import embed_one


# Everyday words that say nothing about a topic. Ignoring them keeps keyword search focused.
STOPWORDS = frozenset(
    "a an and are as at be but by do does did for from had has have how i in is it its many much of on or "
    "so than that the their there these this to was were what when where which who why will with you".split()
)


def _stem(word: str) -> str:
    """Chop simple endings so "labels", "labeled" and "label" all match each other.

    Only chops when at least 3 letters remain, so short words are left alone.
    """
    for ending in ("ing", "ed", "s"):
        if word.endswith(ending) and not word.endswith("ss") and len(word) - len(ending) >= 3:
            return word[: -len(ending)]
    return word


def tokenize(text: str) -> list[str]:
    """Break text into comparable words: lower case, no punctuation, no filler words, simple stemming.

    Numbers like "91.5" stay whole.
    """
    words = re.findall(r"[a-z0-9]+(?:\.[0-9]+)?", text.lower())
    return [_stem(w) for w in words if w not in STOPWORDS]


class _SafeBM25(BM25Okapi):
    """BM25 whose word-rarity score can never go negative.

    The stock version treats a word that appears in more than half of the chunks as
    "worthless" (negative score). In a short paper that throws away real matches, and with a
    single chunk it finds nothing at all. This variant still prefers rare words but always
    counts a match as a positive.
    """

    def _calc_idf(self, nd):
        for word, doc_count in nd.items():
            self.idf[word] = math.log(1 + (self.corpus_size - doc_count + 0.5) / (doc_count + 0.5))


def bm25_rank(texts: list[str], question: str, limit: int) -> list[int]:
    """Rank texts by keyword match. Returns the positions of the best matches, best first.

    Texts that share no word with the question are left out.
    """
    if not texts:
        return []
    scores = _SafeBM25([tokenize(t) for t in texts]).get_scores(tokenize(question))
    order = sorted(range(len(texts)), key=lambda i: scores[i], reverse=True)
    return [i for i in order[:limit] if scores[i] > 0]


def rrf(rank_lists: list[list[str]], k: int = 60) -> list[str]:
    """Merge several ranked lists into one. Items near the top of many lists float to the top."""
    scores: dict[str, float] = {}
    for ranking in rank_lists:
        for rank, item_id in enumerate(ranking, start=1):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
    return [item_id for item_id, _ in sorted(scores.items(), key=lambda kv: kv[1], reverse=True)]


def find_chunks(
    db: Session, user_id: UUID, document_id: UUID, question: str, k: int | None = None
) -> list[Chunk]:
    """Return the `k` most useful chunks of one paper for this question."""
    k = k or settings.retrieve_k
    stored = chunk_repo.list_for_document(db, document_id)
    if not stored:
        return []

    by_id = {str(c.id): c for c in stored}

    # 1) Meaning search. If Ollama's embedding model is unavailable we simply skip this
    #    searcher and rely on keywords, so chat still works.
    semantic_ids: list[str] = []
    try:
        result = get_collection().query(
            query_embeddings=[embed_one(question)],
            n_results=min(k * 2, len(stored)),
            where={"$and": [{"document_id": str(document_id)}, {"user_id": str(user_id)}]},
        )
        semantic_ids = result.get("ids", [[]])[0]
    except Exception:
        semantic_ids = []

    # 2) Keyword search.
    keyword_ids = [str(stored[i].id) for i in bm25_rank([c.text for c in stored], question, k * 2)]

    # 3) Merge and keep the top k.
    picked = [by_id[item_id] for item_id in rrf([semantic_ids, keyword_ids]) if item_id in by_id]
    return picked[:k]
