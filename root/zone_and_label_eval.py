import sys
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, recall_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
pd.set_option("display.width", 220); pd.set_option("display.max_columns", None)

b = pd.read_csv(ROOT / "data/interim/kaggle/model_base_v2.csv", parse_dates=["listing_date"])
tr = pd.read_csv(ROOT / "data/interim/gmp/gmp_tracker_all_years.csv", parse_dates=["listing_date"])
b["k"] = b["issue_price"].round(2); tr["k"] = tr["issue_price"].round(2)
b = b.merge(tr[["listing_date", "k", "listing_price_src"]].drop_duplicates(["listing_date", "k"]),
            on=["listing_date", "k"], how="left")
b["flat"] = b["listing_gain_pct"] == 0
b["conflict"] = b["flat"] & b["listing_price_src"].notna() & ((b["listing_price_src"] - b["issue_price"]).abs() > 0.5)

# ---------- 1) rows that need a manual check ----------
chk = b[b["conflict"] | (b["flat"] & b["listing_price_src"].isna())].copy()
chk["why"] = np.where(chk["conflict"], "tracker price differs", "no tracker price")
chk["date"] = chk["listing_date"].dt.strftime("%Y-%m-%d")
print(f"Flat listings to verify against NSE/BSE: {len(chk)}")
print(chk[["date", "company_name", "issue_price", "listing_price", "listing_price_src", "why"]].to_string(index=False))

# ---------- 2) model under three label definitions ----------
d = b[(b["listing_year"] >= 2020) & b["gmp_pct_of_issue"].notna() & b["log_total"].notna()].reset_index(drop=True)
FEATS = ["gmp_pct_of_issue", "log_total", "log_issue_size", "nifty_ret_20d", "recent_gain_mean10"]
LABELS = {"strict (gain > 0)": d,
          "drop price conflicts": d[~d["conflict"]],
          "clear only (|gain| > 2%)": d[d["listing_gain_pct"].abs() > 2]}

def walk(df):
    parts = []
    for yr in range(2022, 2027):
        trn, te = df[df["listing_year"] < yr], df[df["listing_year"] == yr].copy()
        if len(trn) < 40 or te.empty or trn["y"].nunique() < 2:
            continue
        m = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                          LogisticRegression(max_iter=1000, class_weight="balanced"))
        te["p"] = m.fit(trn[FEATS], trn["y"]).predict_proba(te[FEATS])[:, 1]
        parts.append(te)
    return pd.concat(parts)

rows = []
for name, df in LABELS.items():
    df = df.assign(y=(df["listing_gain_pct"] > 0).astype(int))
    te = walk(df)
    for zone, mask in [("all", te["gmp_pct_of_issue"].notna()),
                       ("GMP <= 10% zone", te["gmp_pct_of_issue"] <= 10),
                       ("GMP > 10%", te["gmp_pct_of_issue"] > 10)]:
        t = te[mask]
        if t["y"].nunique() < 2:
            continue
        yh = (t["p"] >= 0.5).astype(int)
        rows.append({"labels": name, "slice": zone, "n": len(t), "positive": t["y"].mean(),
                     "model_auc": roc_auc_score(t["y"], t["p"]),
                     "gmp_only_auc": roc_auc_score(t["y"], t["gmp_pct_of_issue"]),
                     "subscription_only_auc": roc_auc_score(t["y"], t["log_total"]),
                     "downside_recall": recall_score(t["y"], yh, pos_label=0, zero_division=0),
                     "f1_negative": f1_score(t["y"], yh, pos_label=0, zero_division=0)})
print("\nWalk-forward logistic regression, test years 2022-2026:")
print(pd.DataFrame(rows).round(3).to_string(index=False))