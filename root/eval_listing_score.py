import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.evaluation.harness import REF, bootstrap_deltas, core_metrics, load_eval_frame, to_md, walk_forward
from src.fundamental_analysis.scoring import ListingInputs, score_listing

frame = load_eval_frame(ROOT / "data/interim/kaggle/model_base_v3.csv")
frame["listing_score"] = [score_listing(ListingInputs(gmp_pct=r.gmp_pct_of_issue, qib_sub=r.qib_sub, total_sub=r.total_sub,
                                                      nifty_ret_20d=r.nifty_ret_20d, issue_size_cr=r.issue_size_cr))["score"]
                          for r in frame.itertuples()]

pred, _ = walk_forward(frame)
NAME = "Checklist listing score (logistic on the score)"
probs, scores = [], []
for yr in sorted(pred["listing_year"].unique()):
    tr, te = frame[frame["listing_year"] < yr], frame[frame["listing_year"] == yr]
    m = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)).fit(tr[["listing_score"]], tr["y"])
    probs.append(m.predict_proba(te[["listing_score"]])[:, 1]); scores.append(te["listing_score"].to_numpy())
pred[f"p::{NAME}"] = np.concatenate(probs)
pred["listing_score"] = np.concatenate(scores)

board = pd.DataFrame([{"model": n, **core_metrics(pred["y"], pred[f"p::{n}"])} for n in (REF, NAME)])
delta = pd.DataFrame([{"model": NAME, **bootstrap_deltas(pred, f"p::{REF}", f"p::{NAME}", n_boot=1000, by="quarter")}])
z = pred[pred["gmp_pct_of_issue"] <= 10]
zone = pd.DataFrame([{"slice": f"GMP <= 10% (n={len(z)})", "AUC listing score": roc_auc_score(z["y"], z["listing_score"]),
                      "AUC GMP alone": roc_auc_score(z["y"], z["gmp_pct_of_issue"])}])
frame["Checklist band"] = pd.cut(frame["listing_score"], [-np.inf, 60, 70, 80, np.inf], right=False,
                                 labels=["below 60: Weak", "60-69: Uncertain", "70-79: Good", "80+: Strong"])
bands = (frame.groupby("Checklist band", observed=True)
         .agg(IPOs=("y", "size"), positive_rate=("y", "mean"), median_gain=("listing_gain_pct", "median")).reset_index())

text = "\n".join(["# Checklist listing score as a baseline (auto-generated)", "",
                 f"Test rows {len(pred)}. The score is untrained (weights from the checklist, heuristic mapping); "
                 "a one-feature logistic regression only converts it to a probability.", "",
                 to_md(board), "", "Difference vs GMP-only (quarter-block bootstrap):", to_md(delta), "",
                 "Inside the weak GMP zone:", to_md(zone), "",
                 f"Outcomes by checklist band, all {len(frame)} IPOs with a GMP:", to_md(bands), ""])
(ROOT / "reports/evaluation/listing_score_baseline.md").write_text(text, encoding="utf-8")
print(text)