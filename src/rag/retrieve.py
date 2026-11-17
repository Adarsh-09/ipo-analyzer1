"""Hybrid retrieval: BM25 keyword ranking and dense embedding ranking, fused with reciprocal rank fusion."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
from rank_bm25 import BM25Okapi

from src.rag.index import RAG_DIR, collection_name, get_chroma_client, load_chunks


def tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def rrf(rank_lists: Sequence[Sequence[str]], k: int = 60) -> List[Tuple[str, float]]:
    """Reciprocal rank fusion: an item scores the sum of 1 / (k + rank) over the lists that contain it."""
    scores: Dict[str, float] = {}
    for ranking in rank_lists:
        for rank, item in enumerate(ranking, start=1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda kv: kv[1], reverse=True)


class HybridRetriever:
    def __init__(self, doc_id: str, embedder, store_dir=None, chroma_client=None):
        self.doc_id, self.embedder = doc_id, embedder
        self.chunks = load_chunks(doc_id, store_dir)
        self.by_id = {c["chunk_id"]: c for c in self.chunks}
        self.bm25 = BM25Okapi([tokenize(c["text"]) for c in self.chunks])
        client = chroma_client or get_chroma_client(Path(store_dir or RAG_DIR) / "chroma")
        self.col = client.get_collection(collection_name(doc_id))

    def search(self, query: str, k: int = 6, pool: int = 25) -> List[Dict]:
        qv = self.embedder.encode([query])[0]
        dense = self.col.query(query_embeddings=[qv.tolist()], n_results=min(pool, self.col.count()))["ids"][0]
        scores = self.bm25.get_scores(tokenize(query))
        bm = [self.chunks[i]["chunk_id"] for i in np.argsort(-scores)[:pool] if scores[i] > 0]
        hits = []
        for cid, score in rrf([dense, bm])[:k]:
            hits.append({**self.by_id[cid], "score": score,
                         "dense_rank": dense.index(cid) + 1 if cid in dense else None,
                         "bm25_rank": bm.index(cid) + 1 if cid in bm else None})
        return hits