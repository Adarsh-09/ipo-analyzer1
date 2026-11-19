"""PDF text extraction with page numbers and table-aware text preservation.

Public contracts remain unchanged:
    extract_pages(pdf_path) -> [{'page': int, 'text': str}, ...]
    clean_pages(pages) -> [{'page': int, 'text': str}, ...]

PyMuPDF table extraction is optional and falls back to normal text.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Dict, List


_TABLE_START = re.compile(r"^\[TABLE\s+\d+\s+START\]$", re.I)
_TABLE_END = re.compile(r"^\[TABLE\s+\d+\s+END\]$", re.I)

_NUM_ONLY = re.compile(
    r"^\s*(page\s*)?\d+(\s*of\s*\d+)?\s*$",
    re.I
)


def _pdf_lib():
    try:
        import pymupdf
        return pymupdf
    except ImportError:
        import fitz
        return fitz


def _normalise_cell(value) -> str:
    if value is None:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(value)
    ).strip()


def _extract_tables(page) -> str:
    """Extract tables as page-local, pipe-delimited rows.

    If the installed PyMuPDF version does not support find_tables(),
    or a particular page fails table detection, normal text extraction
    continues without interruption.
    """

    find_tables = getattr(page, "find_tables", None)

    if not callable(find_tables):
        return ""

    try:
        finder = find_tables()
        tables = getattr(finder, "tables", None) or []
    except Exception:
        return ""

    rendered = []

    for table_number, table in enumerate(tables, start=1):

        try:
            raw_rows = table.extract() or []
        except Exception:
            continue

        rows = []

        for raw_row in raw_rows:

            cells = [
                _normalise_cell(cell)
                for cell in (raw_row or [])
            ]

            if any(cells):
                rows.append(" | ".join(cells))

        if len(rows) < 2:
            continue

        rendered.append(
            f"[TABLE {table_number} START]\n"
            + "\n".join(rows)
            + f"\n[TABLE {table_number} END]"
        )

    return "\n\n".join(rendered)


def extract_pages(pdf_path) -> List[Dict]:
    """Extract text and detected tables using 1-based page numbers."""

    lib = _pdf_lib()
    pages = []

    with lib.open(str(pdf_path)) as doc:

        for page_number, page in enumerate(doc, start=1):

            text = page.get_text("text") or ""

            table_text = _extract_tables(page)

            if table_text:

                text = (
                    f"{text.rstrip()}\n\n{table_text}"
                    if text.strip()
                    else table_text
                )

            pages.append({
                "page": page_number,
                "text": text
            })

    return pages


def _norm_line(line: str) -> str:

    return re.sub(
        r"\d+",
        "#",
        re.sub(
            r"\s+",
            " ",
            line.strip().lower()
        )
    )


def _is_table_line(line: str) -> bool:

    stripped = line.strip()

    return bool(
        _TABLE_START.match(stripped)
        or _TABLE_END.match(stripped)
        or "|" in stripped
    )


def clean_pages(
    pages: List[Dict],
    repeat_ratio: float = 0.5,
    min_pages: int = 6
) -> List[Dict]:
    """Remove repeated headers/footers without destroying table structure.

    Page numbers and dictionary fields remain compatible with index.py.
    Newline boundaries are preserved for table-aware chunking.
    """

    if not 0 < repeat_ratio <= 1:
        raise ValueError("repeat_ratio must be in (0, 1].")

    if min_pages < 1:
        raise ValueError("min_pages must be >= 1.")

    repeated = set()

    if len(pages) >= min_pages:

        counts = Counter()

        for page in pages:

            text = str(page.get("text") or "")

            norms = {
                _norm_line(line)
                for line in text.splitlines()
                if (
                    0 < len(line.strip()) < 120
                    and not _is_table_line(line)
                    and not _NUM_ONLY.match(line)
                )
            }

            counts.update(
                n for n in norms
                if re.search(r"[a-z]", n)
            )

        repeated = {
            norm
            for norm, count in counts.items()
            if count >= repeat_ratio * len(pages)
        }

    cleaned = []

    for page in pages:

        page_number = page.get("page")
        text = str(page.get("text") or "")

        kept = []

        for line in text.splitlines():

            stripped = line.strip()

            if not stripped:

                if kept and kept[-1] != "":
                    kept.append("")

                continue

            is_table = _is_table_line(stripped)

            # Do not remove numeric rows inside tables.
            if not is_table and _NUM_ONLY.match(stripped):
                continue

            # Do not remove financial table headers/rows.
            if (
                not is_table
                and _norm_line(stripped) in repeated
            ):
                continue

            kept.append(
                re.sub(r"[ \t]+", " ", stripped)
            )

        cleaned.append({
            "page": page_number,
            "text": "\n".join(kept).strip()
        })

    return cleaned