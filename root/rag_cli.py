import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.rag.answer import answer_question, get_llm_settings
from src.rag.embeddings import default_embedder
from src.rag.index import build_index
from src.rag.questions import CHECKLIST_QUESTIONS, RETRIEVAL_QUERIES
from src.rag.retrieve import HybridRetriever

_seen = set()


def show(retriever, question, query, settings):
    res = answer_question(question, retriever.search(query, k=8), **settings)
    print(f"\nQ: {question}\n[{res['mode']}] {res['answer']}")
    if res["error"] and res["error"] not in _seen:          # print each distinct error once
        _seen.add(res["error"])
        print("Language model call failed:", res["error"][:300])
        if res["hint"]:
            print("Hint:", res["hint"])
    if not res["citations_ok"]:
        print("WARNING: citation check failed. Unsupported pages:", res["unsupported_pages"])
    print("Retrieved pages:", res["pages"])


ap = argparse.ArgumentParser()
sub = ap.add_subparsers(dest="cmd", required=True)
sub.add_parser("index").add_argument("pdf")
a = sub.add_parser("ask"); a.add_argument("doc_id"); a.add_argument("question")
sub.add_parser("checklist").add_argument("doc_id")
args = ap.parse_args()

emb = default_embedder()
if args.cmd == "index":
    print("\n", build_index(args.pdf, emb, progress=lambda d, t: print(f"\rembedded {d}/{t}", end="")))
else:
    r, settings = HybridRetriever(args.doc_id, emb), get_llm_settings()
    if args.cmd == "ask":
        show(r, args.question, args.question, settings)
    else:
        for title, q in CHECKLIST_QUESTIONS.items():
            show(r, q, RETRIEVAL_QUERIES.get(title, q), settings)