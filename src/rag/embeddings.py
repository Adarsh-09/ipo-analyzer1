"""Embedders. Both return L2-normalised vectors, so Chroma's default distance ranks like cosine."""
from __future__ import annotations

import os
import re
import zlib
from typing import List

import numpy as np


class HashingEmbedder:
    """Deterministic bag-of-words embedder for tests and offline use (no model download)."""

    def __init__(self, dim: int = 512):
        self.dim = dim

    def encode(self, texts: List[str]) -> np.ndarray:
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, t in enumerate(texts):
            for w in re.findall(r"[a-z0-9]+", t.lower()):
                out[i, zlib.crc32(w.encode()) % self.dim] += 1.0
        norms = np.linalg.norm(out, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return out / norms


class SentenceTransformerEmbedder:
    """Sentence embeddings. Loads from the local cache when possible (no network call, no Hub warning)."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name, self._model = model_name, None

    def _load(self):
        os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
        os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
        from sentence_transformers import SentenceTransformer
        try:
            from transformers.utils import logging as hf_logging
            hf_logging.disable_progress_bar()
            hf_logging.set_verbosity_error()
        except Exception:
            pass
        try:
            return SentenceTransformer(self.model_name, local_files_only=True)   # already downloaded
        except Exception:
            return SentenceTransformer(self.model_name)                            # first run: download

    def encode(self, texts: List[str]) -> np.ndarray:
        if self._model is None:
            self._model = self._load()
        return np.asarray(self._model.encode(list(texts), batch_size=64, normalize_embeddings=True,
                                             show_progress_bar=False), dtype=np.float32)


def default_embedder() -> SentenceTransformerEmbedder:
    return SentenceTransformerEmbedder()