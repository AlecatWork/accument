"""Cutting pages into small, overlapping pieces ("chunks").

Why: the AI can only read a little at a time, and search works better on short passages.
The overlap is like a repeated sentence at the top of each new page of a book, so an idea
that straddles a cut isn't lost.
"""


def chunk_pages(pages: list[dict], size: int = 900, overlap: int = 150) -> list[dict]:
    """Split each page's text into chunks of about `size` characters.

    Each chunk remembers its page number, so answers can say "see page 3".
    Cuts are moved back to the nearest space so words are never sliced in half.
    """
    if overlap >= size:
        raise ValueError("overlap must be smaller than size")
    chunks = []
    for page in pages:
        text = " ".join(page["text"].split())  
        if not text:
            continue
        start = 0
        index = 0
        while start < len(text):
            end = min(start + size, len(text))
            if end < len(text):
                cut = text.rfind(" ", start + size // 2, end)  
                if cut != -1:
                    end = cut
            piece = text[start:end].strip()
            if piece:
                chunks.append({"page_number": page["page_number"], "chunk_index": index, "text": piece})
                index += 1
            if end >= len(text):
                break
            start = max(end - overlap, start + 1)  
    return chunks
