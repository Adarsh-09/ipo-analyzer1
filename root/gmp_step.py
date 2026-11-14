import ast, sys
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, recall_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "root"))
from src.collection.http_client import IPOHttpClient
from parse_gmp_tracker import parse_tracker_html

pd.set_option("display.width", 220); pd.set_option("display.max_columns", None)

# ---------- 1) fetch (or reuse cached) tracker pages for 2020-2026 ----------
def tracker_url():
    tree = ast.parse((ROOT / "root/inspect_investorgain_gmp_tracker.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "URL" for t in node.targets):
            return ast.literal_eval(node.value)
    raise SystemExit("Could not find URL in inspect_investorgain_gmp_tracker.py")

def page_text(resp):
    c = [v.decode("utf-8", "ignore") if isinstance(v, bytes) else v
         for v in resp.values() if isinstance(v, (str, bytes))]
    return max(c, key=len) if c else ""

RAW = ROOT / "data/raw/gmp"; RAW.mkdir(parents=True, exist_ok=True)
old2020 = ROOT / "data/raw/ipo_master/investorgain_gmp_tracker_2020.html"
url, client, frames = tracker_url(), None, []
print("Tracker URL:", url)

for year in range(2020, 2027):
    cache = RAW / f"tracker_{year}.html"
    if not cache.exists() and year == 2020 and old2020.exists():
        cache.write_text(old2020.read_text(encoding="utf-8", errors="ignore"), encoding="utf-8")
    if not cache.exists():
        client = client or IPOHttpClient(rate_limit_delay=2.0)
        resp = client.get(url, params={"year": year})
        html = page_text(resp)
        if resp.get("status_code") != 200 or "reportTable" not in html:
            print(year, "-> fetch failed, status", resp.get("status_code")); continue
        cache.write_text(html, encoding="utf-8")
    df = parse_tracker_html(cache.read_text(encoding="utf-8", errors="ignore"), year)
    frames.append(df)
    print(f"{year}: {len(df)} tracker rows, {int(df['gmp_rs'].notna().sum())} with a GMP value")

g = pd.concat(frames, ignore_index=True)
g["issue_price_r"] = g["issue_price"].round(2)
g_u = g.drop_duplicates(["listing_date", "issue_price_r"])
g_u.to_csv(ROOT / "data/interim/gmp/gmp_tracker_all_years.csv", index=False)

# ---------- 2) merge into the model base on listing date + issue price ----------
m = pd.read_csv(ROOT / "data/interim/kaggle/model_base.csv", parse_dates=["listing_date"])
m["issue_price_r"] = m["issue_price"].round(2)
keep = g_u[["listing_date", "issue_price_r", "gmp_rs", "gmp_pct_of_issue", "company_name"]]
mm = m.merge(keep.rename(columns={"company_name": "gmp_source_name"}),
             on=["listing_date", "issue_price_r"], how="left")
assert len(mm) == len(m), "merge duplicated rows"
mm["gmp_missing"] = mm["gmp_pct_of_issue"].isna().astype(int)
mm.to_csv(ROOT / "data/interim/kaggle/model_base_gmp.csv", index=False)

print("\nGMP coverage by listing year (model base):")
print(mm.groupby("listing_year").agg(ipos=("listing_gain_pct", "size"),
                                     with_gmp=("gmp_pct_of_issue", lambda s: int(s.notna().sum()))))
chk = g_u[g_u["gmp_rs"].notna()].merge(m[["listing_date", "issue_price_r"]], how="left",
                                       on=["listing_date", "issue_price_r"], indicator=True)
lost = chk[chk["_merge"] == "left_only"]
print(f"\nTracker rows with GMP that did not match the base: {len(lost)}")
print(lost[["listing_date", "company_name", "issue_price", "gmp_rs"]].head(25).to_string())

# ---------- 3) does GMP help? (same rows, walk-forward) ----------
POST = ["log_issue_size", "recent_gain_mean10", "recent_pos_rate10", "recent_gain_mean30",
        "nifty_ret_5d", "nifty_ret_20d", "vix_level", "vix_change_5d",
        "log_qib", "log_nii", "log_retail", "log_total"]
d = mm[mm["gmp_pct_of_issue"].notna()].sort_values("listing_date").reset_index(drop=True)
tests = [y for y in sorted(d["listing_year"].unique()) if y >= 2022]
print(f"\nRows with GMP: {len(d)} | test years: {tests}")

def models():
    return {"logreg": make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                                    LogisticRegression(max_iter=1000, class_weight="balanced")),
            "rf": make_pipeline(SimpleImputer(strategy="median"),
                                RandomForestClassifier(n_estimators=300, min_samples_leaf=5,
                                class_weight="balanced_subsample", random_state=42, n_jobs=-1))}

def evaluate(feats):
    P, T = {"logreg": [], "rf": []}, []
    for y in tests:
        tr, te = d[d["listing_year"] < y], d[d["listing_year"] == y]
        if len(tr) < 40 or tr["listing_positive"].nunique() < 2 or te.empty:
            continue
        T.append(te)
        for k, mdl in models().items():
            mdl.fit(tr[feats], tr["listing_positive"])
            P[k].append(mdl.predict_proba(te[feats])[:, 1])
    te_all, rows = pd.concat(T), []
    for k in P:
        p = np.concatenate(P[k]); yhat = (p >= 0.5).astype(int); y = te_all["listing_positive"]
        rows.append({"model": k, "auc": roc_auc_score(y, p), "acc": accuracy_score(y, yhat),
                     "downside_recall": recall_score(y, yhat, pos_label=0, zero_division=0),
                     "f1_negative": f1_score(y, yhat, pos_label=0, zero_division=0)})
    return te_all, pd.DataFrame(rows).round(3)

te_a, res_a = evaluate(POST)
te_b, res_b = evaluate(POST + ["gmp_pct_of_issue"])
print(f"\nPOST features, no GMP (n={len(te_a)}):\n", res_a.to_string(index=False))
print(f"\nPOST features + GMP (n={len(te_b)}):\n", res_b.to_string(index=False))

y = te_a["listing_positive"]; rule = (te_a["gmp_pct_of_issue"] > 0).astype(int)
print("\nGMP alone | AUC:", round(roc_auc_score(y, te_a["gmp_pct_of_issue"]), 3),
      "| rule 'GMP>0 => positive': acc", round(accuracy_score(y, rule), 3),
      "downside recall", round(recall_score(y, rule, pos_label=0, zero_division=0), 3))
print("Spearman(gmp_pct, listing_gain_pct):",
      round(d["gmp_pct_of_issue"].corr(d["listing_gain_pct"], method="spearman"), 3))