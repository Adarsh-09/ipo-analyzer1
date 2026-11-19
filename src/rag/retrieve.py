"""Hybrid retrieval using existing BM25 + dense search + RRF."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np
from rank_bm25 import BM25Okapi

from src.rag.index import (
    RAG_DIR,
    collection_name,
    get_chroma_client,
    load_chunks,
)


TOKEN_PATTERN = re.compile(
    r"[a-z]+|\d+(?:\.\d+)?",
    re.I
)


# Expand only the BM25 keyword query.
# Dense retrieval continues to use the user's original query.
KEYWORD_EXPANSIONS = {
    "revenue": (
        "turnover sales revenue from operations"
    ),
    "profit after tax": (
        "pat profit for the year net profit attributable"
    ),
    "ebitda": (
        "earnings before interest tax depreciation amortisation"
    ),
    "borrowings": (
        "total debt secured loans unsecured loans"
    ),
    "net worth": (
        "net assets total equity shareholders funds"
    ),
    "operating cash flow": (
        "cash generated from operations cash flow operating activities"
    ),
    "fresh issue": (
        "fresh equity issue new shares primary issue"
    ),
    "offer for sale": (
        "ofs secondary sale selling shareholders"
    ),
    "pledge": (
        "encumbrance shares pledged promoter shareholding"
    ),
    "capital structure": (
        "issued subscribed paid up share capital equity shares"
    ),
    "related party": (
        "ind as 24 related party transactions"
    ),
    "litigation": (
        "outstanding legal proceedings civil criminal tax dispute"
    ),
    "pat": (
    "profit after tax profit for the year net profit attributable"
    ),
}


def tokenize(text: str) -> List[str]:
    """Tokenise text while retaining financial numbers."""

    return TOKEN_PATTERN.findall(
        (text or "").lower()
    )


def expand_keyword_query(query: str) -> str:
    """Expand financial terms for BM25 retrieval."""

    query = (query or "").strip()

    lower = query.lower()

    expansions = []

    for phrase, synonyms in KEYWORD_EXPANSIONS.items():

        if phrase in lower:

            expansions.append(synonyms)

    if not expansions:
        return query

    return query + " " + " ".join(expansions)


def rrf(
    rank_lists: Sequence[Sequence[str]],
    k: int = 60
) -> List[Tuple[str, float]]:
    """Reciprocal rank fusion."""

    if k <= 0:
        raise ValueError("RRF k must be positive.")

    scores: Dict[str, float] = {}

    for ranking in rank_lists:

        for rank, item in enumerate(
            ranking,
            start=1
        ):

            scores[item] = (
                scores.get(item, 0.0)
                + 1.0 / (k + rank)
            )

    return sorted(
        scores.items(),
        key=lambda item: (-item[1], item[0])
    )


class HybridRetriever:

    def __init__(
        self,
        doc_id: str,
        embedder,
        store_dir=None,
        chroma_client=None
    ):

        self.doc_id = doc_id
        self.embedder = embedder

        self.chunks = load_chunks(
            doc_id,
            store_dir
        )

        self.by_id = {
            chunk["chunk_id"]: chunk
            for chunk in self.chunks
        }

        corpus = [
            tokenize(chunk["text"])
            for chunk in self.chunks
        ]

        self.bm25 = (
            BM25Okapi(corpus)
            if corpus and any(corpus)
            else None
        )

        client = chroma_client or get_chroma_client(
            Path(store_dir or RAG_DIR) / "chroma"
        )

        self.col = client.get_collection(
            collection_name(doc_id)
        )


    def search(
        self,
        query: str,
        k: int = 6,
        pool: int = 25
    ) -> List[Dict]:
        """Return hybrid-ranked chunks with existing metadata fields."""

        if not query or not query.strip():
            return []

        if k <= 0 or pool <= 0:
            return []

        if not self.chunks:
            return []

        dense_ids = []
        bm_ids = []

        # -------------------------------------------------
        # DENSE RETRIEVAL
        # -------------------------------------------------

        try:

            collection_count = self.col.count()

        except Exception:

            collection_count = 0

        if collection_count > 0:

            vector = self.embedder.encode(
                [query]
            )[0]

            response = self.col.query(
                query_embeddings=[
                    vector.tolist()
                ],
                n_results=min(
                    pool,
                    collection_count
                )
            )

            result_ids = response.get(
                "ids",
                [[]]
            )

            if result_ids:

                dense_ids = [
                    cid
                    for cid in result_ids[0]
                    if cid in self.by_id
                ]


        # -------------------------------------------------
        # BM25 RETRIEVAL WITH FINANCIAL EXPANSION
        # -------------------------------------------------

        if self.bm25 is not None:

            expanded = expand_keyword_query(
                query
            )

            query_tokens = tokenize(
                expanded
            )

            scores = self.bm25.get_scores(
                query_tokens
            )

            indices = np.argsort(
                -scores,
                kind="stable"
            )[:pool]

            bm_ids = [

                self.chunks[index]["chunk_id"]

                for index in indices

                if scores[index] > 0

            ]


        # -------------------------------------------------
        # RECIPROCAL RANK FUSION
        # -------------------------------------------------

        ranked = rrf([
            dense_ids,
            bm_ids
        ])

        dense_ranks = {
            cid: rank
            for rank, cid in enumerate(
                dense_ids,
                start=1
            )
        }

        bm_ranks = {
            cid: rank
            for rank, cid in enumerate(
                bm_ids,
                start=1
            )
        }

        hits = []

        for cid, score in ranked[:k]:

            if cid not in self.by_id:
                continue

            hits.append({

                **self.by_id[cid],

                "score": score,

                "dense_rank": dense_ranks.get(
                    cid
                ),

                "bm25_rank": bm_ranks.get(
                    cid
                ),

            })

        return hits