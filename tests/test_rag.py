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
from src.rag.extract import (
    clean_pages,
    extract_pages,
    _extract_tables,
)
from src.rag.index import build_index, collection_name, doc_id_from_path
from src.rag.retrieve import HybridRetriever, rrf
from src.rag.retrieve import (
    HybridRetriever,
    rrf,
    expand_keyword_query,
)

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

    def test_table_extraction_preserves_financial_rows(self):
        class FakeTable:
            def extract(self):
                return [
                    ["Particulars", "FY2024", "FY2025"],
                    ["Revenue", "500", "650"],
                    ["PAT", "40", "95"],
                ]

        class FakePage:
            def find_tables(self):
                return SimpleNamespace(tables=[FakeTable()])

        result = _extract_tables(FakePage())
        self.assertIn("[TABLE 1 START]", result)
        self.assertIn("Particulars | FY2024 | FY2025", result)
        self.assertIn("Revenue | 500 | 650", result)
        self.assertIn("[TABLE 1 END]", result)

    def test_financial_table_headers_repeat_across_chunks(self):
        rows = [
            "Particulars | FY2023 | FY2024 | FY2025"
        ]

        rows.extend([
            f"Row{i} | {i * 100} | {i * 110} | {i * 120}"
            for i in range(1, 8)
        ])

        text = (
            "[TABLE 1 START]\n"
            + "\n".join(rows)
            + "\n[TABLE 1 END]"
        )

        cleaned = clean_pages([
            {
                "page": 220,
                "text": text
            }
        ])

        chunks = chunk_pages(
            cleaned,
            "financial_test",
            max_words=20,
            overlap=3,
            min_words=2
        )
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertIn(
                "Particulars | FY2023 | FY2024 | FY2025",
                chunk["text"]
            )
            self.assertLessEqual(
                len(chunk["text"].split()),
                20
            )

    def test_cleanup_preserves_numeric_table_rows(self):
        pages = []
        for page_number in range(1, 7):
            pages.append({
                "page": page_number,
                "text": (
                    "IPO Prospectus Draft\n"
                    "[TABLE 1 START]\n"
                    "Particulars | FY2024\n"
                    "Revenue | 500\n"
                    "PAT | 95\n"
                    "[TABLE 1 END]\n"
                    f"Unique business discussion {page_number}"
                )
            })
        cleaned = clean_pages(pages)
        for page in cleaned:
            self.assertNotIn(
                "IPO Prospectus Draft",
                page["text"]
            )

            self.assertIn(
                "Revenue | 500",
                page["text"]
            )

            self.assertIn(
                "PAT | 95",
                page["text"]
            )

            self.assertIn(
                "\n",
                page["text"]
            )

    def test_names(self):
        self.assertEqual(doc_id_from_path("Data/My RHP (Final) v2.pdf"), "my_rhp_final_v2")
        self.assertRegex(collection_name("my_rhp_final_v2"), r"^[a-zA-Z0-9][a-zA-Z0-9_-]{1,61}[a-zA-Z0-9]$")

    def test_financial_query_expansion(self):

        expanded = expand_keyword_query(
            "financial summary revenue and PAT"
        ).lower()

        self.assertIn("turnover", expanded)
        self.assertIn("profit after tax", expanded)


    def test_empty_query_returns_no_results(self):

        self.assertEqual(
            self.retriever.search(""),
            []
        )

        self.assertEqual(
            self.retriever.search("   "),
            []
        )

    def test_statement_type_detection(self):
        from src.rag.answer import _detect_statement_type
        self.assertEqual(_detect_statement_type("Restated Consolidated Financial Information"), "consolidated")
        self.assertEqual(_detect_statement_type("Standalone Balance Sheet Statement"), "standalone")
        self.assertEqual(_detect_statement_type("General business discussion"), "unspecified")

    def test_evidence_verification_normalization(self):
        from src.rag.answer import _verify_extraction_evidence
        page_texts = {10: 'The company reported revenue of "Rs. 500 crore" for FY2024 — an increase of 25%.'}
        # Verify unicode smart quotes and em-dash normalization
        ev = [{"page": 10, "quote": 'revenue of “Rs. 500 crore” for FY2024 – an increase'}]
        res = _verify_extraction_evidence(ev, page_texts)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["page"], 10)

        # String format verification
        ev_str = ['Page 10: revenue of "Rs. 500 crore" for FY2024']
        res_str = _verify_extraction_evidence(ev_str, page_texts)
        self.assertEqual(len(res_str), 1)

    def test_extraction_status_and_progress_metrics(self):
        sample_results = {
            "Topic1": {"fields": {"f1": {"status": "verified"}, "f2": {"status": "verified"}}},
            "Topic2": {"fields": {"f3": {"status": "verified"}, "f4": {"status": "unverified"}}},
            "Topic3": {"fields": {"f5": {"status": "invalid_json"}}},
            "Topic4": {"fields": {"f6": {"status": "not_found"}}}
        }
        completed = []
        partial = []
        failed = []
        for t, r in sample_results.items():
            tf = r["fields"]
            v = sum(1 for f in tf.values() if f.get("status") == "verified")
            u = sum(1 for f in tf.values() if f.get("status") == "unverified")
            m = sum(1 for f in tf.values() if f.get("status") in ("not_found", "not_generated"))
            err = sum(1 for f in tf.values() if f.get("status") in ("invalid_json", "generation_error"))
            if err > 0 or (u > 0 and v == 0):
                failed.append(t)
            elif u > 0 and v > 0:
                partial.append(t)
            elif v > 0 or m == len(tf):
                completed.append(t)
            else:
                failed.append(t)
        self.assertEqual(completed, ["Topic1", "Topic4"])
        self.assertEqual(partial, ["Topic2"])
        self.assertEqual(failed, ["Topic3"])

if __name__ == "__main__":
    unittest.main()