import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.evaluation.harness import REF, SPECS, bootstrap_deltas, core_metrics, load_eval_frame, to_md, walk_forward

frame = load_eval_frame(ROOT / "data/interim/kaggle/model_base_v3.csv")
pred, _ = walk_forward(frame)
CHAL = {
    "HGB monotone (GMP, subscription)": (
        ["gmp_pct_of_issue", "log_total"],
        lambda: HistGradientBoostingClassifier(max_depth=2, learning_rate=0.05, max_iter=150,
                                               monotonic_cst=[1, 1], random_state=42)),
    "RF on set C features": (
        SPECS["C B + size + market + momentum"],
        lambda: make_pipeline(SimpleImputer(strategy="median"),
                              RandomForestClassifier(n_estimators=400, min_samples_leaf=8, random_state=42, n_jobs=-1))),
}
for name, (feats, mk) in CHAL.items():
    parts = []
    for yr in sorted(pred["listing_year"].unique()):
        tr, te = frame[frame["listing_year"] < yr], frame[frame["listing_year"] == yr]
        parts.append(mk().fit(tr[feats], tr["y"]).predict_proba(te[feats])[:, 1])
    pred[f"p::{name}"] = np.concatenate(parts)

rows, deltas = [], []
for name in [REF] + list(CHAL):
    rows.append({"model": name, **core_metrics(pred["y"], pred[f"p::{name}"])})
for name in CHAL:
    deltas.append({"model": name, **bootstrap_deltas(pred, f"p::{REF}", f"p::{name}", n_boot=1000, by="quarter")})
text = "\n".join(["# Challenger check (auto-generated)", "", f"Test rows {len(pred)}", "", to_md(pd.DataFrame(rows)), "",
                  "Paired difference vs A, quarter-block bootstrap (negative dBrier = better than A):",
                  to_md(pd.DataFrame(deltas)), ""])
(ROOT / "reports/evaluation/challenger_check.md").write_text(text, encoding="utf-8")
print(text)