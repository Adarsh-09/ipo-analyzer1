"""PDF text extraction with page numbers (PyMuPDF) and light cleaning."""
from __future__ import annotations

import re
from collections import Counter
from typing import Dict, List


def _pdf_lib():
    try:
        import pymupdf
        return pymupdf
    except ImportError:          # older PyMuPDF
        import fitz
        return fitz


def extract_pages(pdf_path) -> List[Dict]:
    """[{'page': 1, 'text': ...}, ...] with 1-based page numbers, as shown in a PDF viewer."""
    lib = _pdf_lib()
    pages = []
    with lib.open(str(pdf_path)) as doc:
        for i, page in enumerate(doc, start=1):
            pages.append({"page": i, "text": page.get_text("text")})
    return pages


_NUM_ONLY = re.compile(r"^\s*(page\s*)?\d+(\s*of\s*\d+)?\s*$", re.I)


def _norm_line(line: str) -> str:
    return re.sub(r"\d+", "#", re.sub(r"\s+", " ", line.strip().lower()))


def clean_pages(pages: List[Dict], repeat_ratio: float = 0.5, min_pages: int = 6) -> List[Dict]:
    """Drop page-number lines and headers/footers that repeat on at least `repeat_ratio` of the pages."""
    repeated = set()
    if len(pages) >= min_pages:
        counts = Counter()
        for p in pages:
            norms = {_norm_line(l) for l in p["text"].splitlines() if 0 < len(l.strip()) < 120}
            counts.update(n for n in norms if re.search(r"[a-z]", n))      # never treat pure numbers as headers
        repeated = {n for n, c in counts.items() if c >= repeat_ratio * len(pages)}
    out = []
    for p in pages:
        keep = [s.strip() for s in p["text"].splitlines()
                if s.strip() and not _NUM_ONLY.match(s) and _norm_line(s) not in repeated]
        out.append({"page": p["page"], "text": re.sub(r"[ \t]+", " ", " ".join(keep)).strip()})
    return out