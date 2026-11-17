import re
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.rag.answer import answer_question, build_prompt, check_citations, cited_pages
from src.rag.chunk import chunk_pages
from src.rag.embeddings import HashingEmbedder
from src.rag.extract import clean_pages, extract_pages
from src.rag.index import build_index, collection_name, doc_id_from_path
from src.rag.retrieve import HybridRetriever, rrf

PAGES = [
    "The company designs and manufactures industrial valves for oil and gas customers across India and exports to twenty countries.",
    "Promoter shares pledged: the promoters have pledged twelve percent of their shareholding with lenders as security for borrowings.",
    "Litigation: there is an outstanding indirect tax dispute involving an amount of Rs 45 crore before the appellate tribunal.",
    "Objects of the issue: the net proceeds will be used for repayment of borrowings and general corporate purposes.",
]


def make_pdf(path):
    try:
        import pymupdf as lib
    except ImportError:
        import fitz as lib
    doc = lib.open()
    for text in PAGES:
        page = doc.new_page()
        page.insert_textbox(lib.Rect(50, 50, 550, 780), text, fontsize=11)
    doc.save(str(path))
    doc.close()


class TestRag(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import chromadb
        cls.tmp = tempfile.TemporaryDirectory()
        cls.pdf = Path(cls.tmp.name) / f"test_rhp_{uuid.uuid4().hex[:8]}.pdf"
        make_pdf(cls.pdf)
        cls.doc_id = doc_id_from_path(cls.pdf)
        cls.client, cls.emb = chromadb.EphemeralClient(), HashingEmbedder()
        cls.info = build_index(cls.pdf, cls.emb, store_dir=cls.tmp.name, chroma_client=cls.client)
        cls.retriever = HybridRetriever(cls.doc_id, cls.emb, store_dir=cls.tmp.name, chroma_client=cls.client)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_extract_and_clean(self):
        pages = extract_pages(self.pdf)
        self.assertEqual([p["page"] for p in pages], [1, 2, 3, 4])
        self.assertIn("pledged", pages[1]["text"])
        topics = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel"]
        many = [{"page": i, "text": f"Offer Document Draft\nUnique body sentence {t} describing a topic\n{i}"}
                for i, t in enumerate(topics, start=1)]
        cleaned = clean_pages(many)
        for p in cleaned:
            self.assertNotIn("Offer Document Draft", p["text"])
            self.assertNotEqual(p["text"].strip(), str(p["page"]))
        self.assertIn("Unique body sentence alpha", cleaned[0]["text"])

    def test_chunking_keeps_pages_and_overlap(self):
        words = " ".join(f"w{i}" for i in range(400))
        ch = chunk_pages([{"page": 7, "text": words}], "doc", max_words=180, overlap=30)
        self.assertTrue(all(len(c["text"].split()) <= 180 for c in ch))
        self.assertEqual({c["page"] for c in ch}, {7})
        self.assertEqual(len({c["chunk_id"] for c in ch}), len(ch))
        self.assertEqual(ch[0]["text"].split()[-30:], ch[1]["text"].split()[:30])

    def test_rrf_prefers_items_ranked_high_in_both(self):
        ids = [i for i, _ in rrf([["a", "b", "c"], ["b", "a", "d"]])]
        self.assertEqual(set(ids[:2]), {"a", "b"})

    def test_hashing_embedder_is_normalised_and_similar_texts_score_higher(self):
        v = self.emb.encode(["promoter pledge shares", "promoter pledged shares", "valves for oil and gas"])
        self.assertTrue(np.allclose(np.linalg.norm(v, axis=1), 1.0, atol=1e-5))
        self.assertGreater(float(v[0] @ v[1]), float(v[0] @ v[2]))

    def test_hybrid_search_finds_the_right_pages(self):
        h = self.retriever.search("promoters pledged shares lenders", k=3)
        self.assertEqual(h[0]["page"], 2)
        self.assertIsNotNone(h[0]["bm25_rank"]); self.assertIsNotNone(h[0]["dense_rank"])
        self.assertEqual(self.retriever.search("Rs 45 crore tax dispute", k=3)[0]["page"], 3)

    def test_prompt_and_citation_checks(self):
        hits = self.retriever.search("objects of the issue", k=2)
        prompt = build_prompt("What are the objects?", hits)
        self.assertIn("What are the objects?", prompt)
        self.assertIn(f"[p. {hits[0]['page']}]", prompt)
        self.assertEqual(cited_pages("see [p. 2] and [pp. 4-6] and [p.9]"), {2, 4, 5, 6, 9})
        chk = check_citations("Pledged [p. 2]. Also [p. 99].", [{"page": 2, "text": "x"}])
        self.assertEqual(chk["unsupported"], [99]); self.assertTrue(chk["has_citation"])

    def test_answer_modes_and_fallback(self):
        hits = self.retriever.search("promoter pledge", k=3)
        r = answer_question("promoter pledge?", hits, api_key=None)
        self.assertEqual(r["mode"], "retrieval-only"); self.assertTrue(r["pages"])

        class Ok:
            models = SimpleNamespace(generate_content=lambda **kw: SimpleNamespace(text="Twelve percent pledged [p. 2]."))
        g = answer_question("q", hits, api_key="x", client=Ok())
        self.assertEqual(g["mode"], "gemini"); self.assertTrue(g["citations_ok"])

        class Wrong:
            models = SimpleNamespace(generate_content=lambda **kw: SimpleNamespace(text="Something [p. 77]."))
        self.assertFalse(answer_question("q", hits, api_key="x", client=Wrong())["citations_ok"])

        def boom(**kw):
            raise RuntimeError("quota exceeded")

        class Broken:
            models = SimpleNamespace(generate_content=boom)
        b = answer_question("q", hits, api_key="x", client=Broken())
        self.assertEqual(b["mode"], "retrieval-only"); self.assertIn("quota", b["error"])
        self.assertEqual(answer_question("q", [], api_key="x")["mode"], "no-hits")

    def test_names(self):
        self.assertEqual(doc_id_from_path("Data/My RHP (Final) v2.pdf"), "my_rhp_final_v2")
        self.assertRegex(collection_name("my_rhp_final_v2"), r"^[a-zA-Z0-9][a-zA-Z0-9_-]{1,61}[a-zA-Z0-9]$")


if __name__ == "__main__":
    unittest.main()