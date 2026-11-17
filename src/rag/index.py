"""Build and locate the on-disk index for one prospectus: chunk file (for BM25) plus a Chroma collection."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Callable, Dict, List, Optional

from src.rag.chunk import chunk_pages
from src.rag.extract import clean_pages, extract_pages

ROOT = Path(__file__).resolve().parents[2]
RAG_DIR = ROOT / "data/rag"


def doc_id_from_path(path) -> str:
    return re.sub(r"[^a-z0-9]+", "_", Path(path).stem.lower()).strip("_")[:50] or "document"


def collection_name(doc_id: str) -> str:
    name = re.sub(r"[^a-zA-Z0-9_-]", "_", f"rhp_{doc_id}")[:60].strip("_-")
    return name if len(name) >= 3 else "rhp_doc"


def chunks_path(doc_id: str, store_dir=None) -> Path:
    return Path(store_dir or RAG_DIR) / "docs" / doc_id / "chunks.jsonl"


def index_exists(doc_id: str, store_dir=None) -> bool:
    return chunks_path(doc_id, store_dir).exists()


def load_chunks(doc_id: str, store_dir=None) -> List[Dict]:
    with chunks_path(doc_id, store_dir).open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def get_chroma_client(path):
    import chromadb
    Path(path).mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(path))


def build_index(pdf_path, embedder, doc_id: Optional[str] = None, store_dir=None, chroma_client=None,
                batch: int = 256, progress: Optional[Callable[[int, int], None]] = None) -> Dict:
    store = Path(store_dir or RAG_DIR)
    doc_id = doc_id or doc_id_from_path(pdf_path)
    pages = clean_pages(extract_pages(pdf_path))
    chunks = chunk_pages(pages, doc_id)
    if not chunks:
        raise ValueError("No extractable text found. The PDF may be scanned; this project needs a text PDF.")
    cp = chunks_path(doc_id, store)
    cp.parent.mkdir(parents=True, exist_ok=True)
    with cp.open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    client = chroma_client or get_chroma_client(store / "chroma")
    name = collection_name(doc_id)
    try:
        client.delete_collection(name)
    except Exception:
        pass
    col = client.create_collection(name=name)
    for i in range(0, len(chunks), batch):
        part = chunks[i:i + batch]
        col.add(ids=[c["chunk_id"] for c in part],
                embeddings=embedder.encode([c["text"] for c in part]).tolist(),
                documents=[c["text"] for c in part],
                metadatas=[{"page": c["page"], "doc_id": doc_id} for c in part])
        if progress:
            progress(min(i + batch, len(chunks)), len(chunks))
    return {"doc_id": doc_id, "pages": len(pages), "chunks": len(chunks), "collection": name}