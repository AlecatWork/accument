"""Print the last full evaluation as a Markdown table."""

import json
from pathlib import Path


def main() -> None:
    rows = json.loads(Path(__file__).with_name("last_report.json").read_text())
    print("| id | pass | answer (first 80 characters) |")
    print("| --- | --- | --- |")
    for row in rows:
        flag = "yes" if row["ok"] else "no"
        excerpt = row["answer"].replace("|", " ").replace("\n", " ")[:80]
        print(f"| {row['id']} | {flag} | {excerpt} |")


if __name__ == "__main__":
    main()