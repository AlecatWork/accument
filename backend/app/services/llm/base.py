"""The shape every "writer" (AI model) must follow, so we can swap Ollama for a hosted model."""

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass


@dataclass
class Generation:
    """A finished piece of writing, plus how much reading/writing the AI did (for the diary)."""

    text: str
    prompt_tokens: int | None = None  # "tokens" are roughly word-pieces; ~3/4 of a word each
    completion_tokens: int | None = None


class Writer(ABC):
    """Anything that can turn a prompt into text."""

    @abstractmethod
    def generate(self, prompt: str) -> Generation:
        """Write the whole answer in one go."""

    @abstractmethod
    def stream(self, prompt: str) -> Iterator[tuple[str, object]]:
        """Write the answer piece by piece.

        Yields ("token", "some text") for every piece, then one ("usage", {...}) at the very end.
        """

    def write(self, prompt: str) -> str:
        """Convenience: just the text."""
        return self.generate(prompt).text
