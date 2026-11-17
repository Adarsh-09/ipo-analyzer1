"""Split cleaned pages into overlapping word chunks that keep their page number."""
from __future__ import annotations

from typing import Dict, List


def chunk_pages(pages: List[Dict], doc_id: str, max_words: int = 180, overlap: int = 30,
                min_words: int = 8) -> List[Dict]:
    if overlap >= max_words:
        raise ValueError("overlap must be smaller than max_words")
    step, chunks = max_words - overlap, []
    for p in pages:
        words = p["text"].split()
        if len(words) < min_words:
            continue
        for j, start in enumerate(range(0, len(words), step)):
            piece = words[start:start + max_words]
            if len(piece) < min_words:
                break
            chunks.append({"chunk_id": f"{doc_id}:{p['page']}:{j}", "doc_id": doc_id,
                           "page": p["page"], "text": " ".join(piece)})
            if start + max_words >= len(words):
                break
    return chunks