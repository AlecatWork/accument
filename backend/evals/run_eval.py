"""The full "does the whole app answer correctly?" check. Needs the app running AND Ollama open.

It logs in as the demo user, asks every golden question about the widget paper, and checks that the
answer contains the expected words. Takes a few minutes on a laptop.

    docker compose exec backend python -m evals.run_eval
    docker compose exec backend python -m evals.run_eval --min-score 0.7   # exit with an error if worse

Writes evals/last_report.json; `python -m evals.report` prints it as a table for the README.
"""

import argparse
import json
import sys
from pathlib import Path

import httpx

BACKEND = "http://localhost:8000"
EMAIL = "demo@example.com"
PASSWORD = "demodemo123"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-score", type=float, default=0.0)
    args = parser.parse_args()

    golden = json.loads(Path(__file__).with_name("golden_set.json").read_text())
    client = httpx.Client(timeout=600)
    login = client.post(f"{BACKEND}/auth/login", json={"email": EMAIL, "password": PASSWORD})
    login.raise_for_status()
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    papers = client.get(f"{BACKEND}/papers", headers=headers).json()
    paper = next(p for p in papers if golden["paper_title"] in (p.get("title") or p["filename"]))

    rows = []
    for item in golden["items"]:
        reply = client.post(
            f"{BACKEND}/chat/ask",
            headers=headers,
            json={"document_id": paper["id"], "question": item["question"]},
        )
        reply.raise_for_status()
        result = reply.json()
        answer = result["answer"].lower()
        ok = all(word.lower() in answer for word in item["must_include"])
        rows.append({"id": item["id"], "ok": ok, "answer": result["answer"][:240]})
        print(f"{'PASS' if ok else 'FAIL'}  #{item['id']:>2}  {item['question']}")

    Path(__file__).with_name("last_report.json").write_text(json.dumps(rows, indent=2))
    score = sum(r["ok"] for r in rows) / len(rows)
    print(f"\nScore: {score:.0%} ({sum(r['ok'] for r in rows)}/{len(rows)})")
    if score < args.min_score:
        sys.exit(1)


if __name__ == "__main__":
    main()
