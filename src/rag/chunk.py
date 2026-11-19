"""Page-local overlapping chunks with financial-table preservation."""

from __future__ import annotations

import re
from typing import Dict, List


_TABLE_START = re.compile(
    r"^\[TABLE\s+(\d+)\s+START\]$",
    re.I
)

_TABLE_END = re.compile(
    r"^\[TABLE\s+(\d+)\s+END\]$",
    re.I
)


def _word_chunks(
    text: str,
    max_words: int,
    overlap: int,
    min_words: int
) -> List[str]:

    words = text.split()

    if len(words) < min_words:
        return []

    step = max_words - overlap
    result = []

    for start in range(0, len(words), step):

        piece = words[start:start + max_words]

        if len(piece) < min_words:
            break

        result.append(" ".join(piece))

        if start + max_words >= len(words):
            break

    return result


def _table_word_count(lines: List[str]) -> int:

    return sum(
        len(line.split())
        for line in lines
    )


def _split_long_table_row(
    row: str,
    max_words: int
) -> List[str]:

    words = row.split()

    if len(words) <= max_words:
        return [row]

    return [
        " ".join(words[i:i + max_words])
        for i in range(0, len(words), max_words)
    ]


def _table_chunks(
    table_number: str,
    rows: List[str],
    max_words: int
) -> List[str]:
    """Chunk tables by complete rows and repeat column headers."""

    rows = [
        row.strip()
        for row in rows
        if row.strip()
    ]

    if len(rows) < 2:
        return []

    header = rows[0]
    body_rows = rows[1:]
    prefix = f"[FINANCIAL TABLE {table_number}]"

    chunks = []
    current = [prefix, header]
    has_data_row = False

    for row in body_rows:

        if len(row.split()) > max_words:

            row_parts = _word_chunks(
                row,
                max_words=max_words,
                overlap=0,
                min_words=1
            )

        else:
            row_parts = [row]

        for row_part in row_parts:

            proposed = current + [row_part]

            if (
                has_data_row
                and _table_word_count(proposed) > max_words
            ):

                chunks.append(
                    "\n".join(current)
                )

                current = [
                    prefix,
                    header
                ]

                has_data_row = False

            current.append(row_part)
            has_data_row = True

    if has_data_row:

        chunks.append(
            "\n".join(current)
        )

    return chunks

def _page_segments(text: str):
    """Separate normal text from marked table blocks."""

    lines = (text or "").splitlines()

    normal_lines = []
    table_lines = []

    table_number = "1"
    in_table = False

    def flush_normal():

        nonlocal normal_lines

        content = "\n".join(
            normal_lines
        ).strip()

        normal_lines = []

        if content:
            yield ("text", content)

    for line in lines:

        stripped = line.strip()

        start_match = _TABLE_START.match(stripped)
        end_match = _TABLE_END.match(stripped)

        if start_match:

            yield from flush_normal()

            in_table = True
            table_number = start_match.group(1)
            table_lines = []

            continue

        if end_match and in_table:

            yield (
                "table",
                (table_number, table_lines)
            )

            in_table = False
            table_lines = []

            continue

        if in_table:

            table_lines.append(stripped)

        else:

            normal_lines.append(line)

    if in_table and table_lines:

        yield (
            "table",
            (table_number, table_lines)
        )

    yield from flush_normal()


def chunk_pages(
    pages: List[Dict],
    doc_id: str,
    max_words: int = 180,
    overlap: int = 30,
    min_words: int = 8
) -> List[Dict]:
    """Build page-local chunks with the existing metadata contract."""

    if max_words < 1:
        raise ValueError("max_words must be >= 1")

    if overlap < 0 or overlap >= max_words:
        raise ValueError(
            "overlap must be >= 0 and smaller than max_words"
        )

    if min_words < 1:
        raise ValueError("min_words must be >= 1")

    chunks = []

    for page in pages:

        page_number = page["page"]
        sequence = 0

        for kind, content in _page_segments(
            page.get("text", "")
        ):

            if kind == "text":

                pieces = _word_chunks(
                    content,
                    max_words,
                    overlap,
                    min_words
                )

            else:

                table_number, rows = content

                pieces = _table_chunks(
                    table_number,
                    rows,
                    max_words
                )

            for piece in pieces:

                chunks.append({

                    "chunk_id": (
                        f"{doc_id}:{page_number}:{sequence}"
                    ),

                    "doc_id": doc_id,

                    "page": page_number,

                    "text": piece

                })

                sequence += 1

    return chunks