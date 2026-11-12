"""The "does search still find the right page?" check. Runs anywhere: no database, no AI needed.

For each question in golden_set.json that has a known page, we search the sample paper with the
keyword searcher and check that:
  1. one of the top results comes from the right page, and
  2. the results actually contain the answer words ("must_include").

Run it:        python -m evals.retrieval_eval
CI runs it with a floor, and the build FAILS if the score drops below it:
               python -m evals.retrieval_eval --min-score 0.9
"""

import argparse
import json
import sys
from pathlib import Path

from app.services.chunker import chunk_pages
from app.services.retriever import bm25_rank
from scripts.sample_papers import SAMPLES

TOP_K = 2  # how many results we're allowed to look at, like the first screen of search results


def run(top_k: int = TOP_K) -> tuple[float, list[dict]]:
    """Return (score between 0 and 1, one result row per question)."""
    golden = json.loads(Path(__file__).with_name("golden_set.json").read_text())
    sample = next(s for s in SAMPLES if s["filename"].startswith(golden["paper_title"]))
    pages = [{"page_number": i, "text": text} for i, text in enumerate(sample["pages"], start=1)]
    chunks = chunk_pages(pages)

    rows = []
    for item in golden["items"]:
        if item["page"] is None:  # "the paper doesn't say" questions are checked by the full eval, not here
            continue
        ranked = bm25_rank([c["text"] for c in chunks], item["question"], top_k)
        found = [chunks[i] for i in ranked]
        right_page = any(c["page_number"] == item["page"] for c in found)
        has_words = all(
            word.lower() in " ".join(c["text"] for c in found).lower() for word in item["must_include"]
        )
        rows.append({"id": item["id"], "question": item["question"], "ok": right_page and has_words})
    score = sum(r["ok"] for r in rows) / len(rows)
    return score, rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-score", type=float, default=0.0, help="exit with an error below this score")
    args = parser.parse_args()

    score, rows = run()
    for row in rows:
        print(f"{'PASS' if row['ok'] else 'FAIL'}  #{row['id']:>2}  {row['question']}")
    print(f"\nRetrieval score: {score:.0%} ({sum(r['ok'] for r in rows)}/{len(rows)}), top {TOP_K} results")
    if score < args.min_score:
        print(f"Score is below the required {args.min_score:.0%}.")
        sys.exit(1)


if __name__ == "__main__":
    main()
