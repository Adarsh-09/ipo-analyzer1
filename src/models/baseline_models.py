import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (accuracy_score, f1_score, mean_absolute_error,
                             recall_score, roc_auc_score)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

df = pd.read_csv("E:/ipo-analyzer1/data/interim/kaggle/model_base.csv")
PRE = ["log_issue_size", "recent_gain_mean10", "recent_pos_rate10", "recent_gain_mean30",
       "nifty_ret_5d", "nifty_ret_20d", "vix_level", "vix_change_5d"]
POST = PRE + ["log_qib", "log_nii", "log_retail", "log_total"]
df = df.dropna(subset=["log_total"]).reset_index(drop=True)   # same rows for both sets

def imp(m, scale=False):
    steps = [SimpleImputer(strategy="median")] + ([StandardScaler()] if scale else []) + [m]
    return make_pipeline(*steps)

classifiers = {
    "majority": lambda: DummyClassifier(strategy="most_frequent"),
    "logreg": lambda: imp(LogisticRegression(max_iter=1000, class_weight="balanced"), True),
    "rf": lambda: imp(RandomForestClassifier(n_estimators=300, min_samples_leaf=5,
                      class_weight="balanced_subsample", random_state=42, n_jobs=-1)),
}
regressors = {
    "median": lambda: DummyRegressor(strategy="median"),
    "ridge": lambda: imp(Ridge(alpha=10.0), True),
    "rf": lambda: imp(RandomForestRegressor(n_estimators=300, min_samples_leaf=5,
                      random_state=42, n_jobs=-1)),
}

TEST_YEARS = range(2021, 2027)

def walk_forward(feats):
    preds = {f"clf_{k}": [] for k in classifiers}
    preds.update({f"reg_{k}": [] for k in regressors})
    keep = []
    for y in TEST_YEARS:
        tr, te = df[df["listing_year"] < y], df[df["listing_year"] == y]
        if te.empty:
            continue
        keep.append(te)
        for k, mk in classifiers.items():
            m = mk().fit(tr[feats], tr["listing_positive"])
            preds[f"clf_{k}"].append(m.predict_proba(te[feats])[:, 1])
        for k, mk in regressors.items():
            m = mk().fit(tr[feats], tr["listing_gain_pct"])
            preds[f"reg_{k}"].append(m.predict(te[feats]))
    te_all = pd.concat(keep)
    return te_all, {k: np.concatenate(v) for k, v in preds.items()}

def report(name, te_all, preds, mask=None):
    te = te_all if mask is None else te_all[mask]
    rows = []
    for k in classifiers:
        p = preds[f"clf_{k}"] if mask is None else preds[f"clf_{k}"][mask.values]
        yhat = (p >= 0.5).astype(int)
        y = te["listing_positive"]
        rows.append({"model": k, "acc": accuracy_score(y, yhat),
                     "auc": roc_auc_score(y, p) if k != "majority" else 0.5,
                     "downside_recall": recall_score(y, yhat, pos_label=0, zero_division=0),
                     "f1_negative": f1_score(y, yhat, pos_label=0, zero_division=0)})
    print(f"\n=== {name}: classification (n={len(te)}) ===")
    print(pd.DataFrame(rows).round(3).to_string(index=False))
    rows = []
    for k in regressors:
        p = preds[f"reg_{k}"] if mask is None else preds[f"reg_{k}"][mask.values]
        rows.append({"model": k, "MAE_pct_points": mean_absolute_error(te["listing_gain_pct"], p)})
    print(f"--- {name}: regression ---")
    print(pd.DataFrame(rows).round(2).to_string(index=False))

for label, feats in [("PRE (no subscription)", PRE), ("POST (with subscription)", POST)]:
    te_all, preds = walk_forward(feats)
    report(label + " | all test years 2021-2026", te_all, preds)
    recent = te_all["listing_year"] >= 2025
    report(label + " | 2025-2026 only", te_all, preds, recent)