import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.rag.embeddings import default_embedder
from src.rag.questions import CHECKLIST_QUESTIONS, RETRIEVAL_QUERIES
from src.rag.retrieve import HybridRetriever

doc_id = sys.argv[1]
gold_path = ROOT / "data/rag" / f"gold_{doc_id}.json"
retriever = HybridRetriever(doc_id, default_embedder())

if not gold_path.exists():
    gold_path.write_text(json.dumps({t: {"acceptable_pages": []} for t in CHECKLIST_QUESTIONS}, indent=2), encoding="utf-8")
    print(f"Wrote {gold_path}. For each question list every page that really answers it (check the PDF), then rerun.\n")
    for t, q in CHECKLIST_QUESTIONS.items():
        print(f"{t}: retrieved {[h['page'] for h in retriever.search(RETRIEVAL_QUERIES.get(t, q), k=8)]}")
    sys.exit()

gold, rows = json.loads(gold_path.read_text(encoding="utf-8")), []
for t, q in CHECKLIST_QUESTIONS.items():
    ok = set(gold.get(t, {}).get("acceptable_pages", []))
    if not ok:
        continue
    for label, query in (("natural question", q), ("keyword query", RETRIEVAL_QUERIES.get(t, q))):
        pages = [h["page"] for h in retriever.search(query, k=8)]
        rank = next((i for i, p in enumerate(pages, 1) if p in ok), None)
        rows.append({"question": t, "query": label, "first_correct_rank": rank})
df = pd.DataFrame(rows)
summary = (df.groupby("query").apply(lambda g: pd.Series({
    "questions": len(g), "hit@3": (g["first_correct_rank"] <= 3).mean(), "hit@5": (g["first_correct_rank"] <= 5).mean(),
    "hit@8": g["first_correct_rank"].notna().mean(),
    "MRR": g["first_correct_rank"].map(lambda r: 0 if pd.isna(r) else 1 / r).mean()})).round(3).reset_index())
print(df.to_string(index=False)); print(); print(summary.to_string(index=False))