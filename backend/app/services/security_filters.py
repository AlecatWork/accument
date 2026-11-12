"""Protection against "prompt injection".

A paper could contain a sentence like "Ignore previous instructions and ...". Because the AI
reads the paper, it might obey. We black out the most common tricks so papers are treated
as content to read, never as orders to follow.
"""

import re

SNEAKY = re.compile(
    r"(ignore (all|any|previous|above) instructions|"
    r"you are now|"
    r"system prompt|"
    r"disregard (the|all) (above|previous))",
    re.IGNORECASE,
)


def clean_paper_text(text: str) -> str:
    """Papers should be read as content, not as orders to the app."""
    cleaned = SNEAKY.sub("[removed]", text)
    return cleaned.replace("\x00", "")


def looks_like_injection(text: str) -> bool:
    """True if the text contains one of the known tricks."""
    return bool(SNEAKY.search(text))