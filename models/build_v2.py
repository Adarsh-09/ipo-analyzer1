import sys
from pathlib import Path
import numpy as np
import pandas as pd
import yfinance as yf
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error, recall_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
GM, KG, MKT = ROOT / "data/interim/gmp", ROOT / "data/interim/kaggle", ROOT / "data/raw/market_context.csv"
pd.set_option("display.width", 220); pd.set_option("display.max_columns", None)

# ---------- 1) Kaggle rows (full history) + GMP from the tracker ----------
k = pd.read_csv(KG / "kaggle_clean_candidates.csv", parse_dates=["listing_date"])
k["data_source"] = "kaggle"
g = pd.read_csv(GM / "gmp_tracker_all_years.csv", parse_dates=["listing_date"])
g["issue_price_r"] = g["issue_price"].round(2); k["issue_price_r"] = k["issue_price"].round(2)
n0 = len(k)
k = k.merge(g[["listing_date", "issue_price_r", "gmp_rs", "gmp_pct_of_issue"]],
            on=["listing_date", "issue_price_r"], how="left")
assert len(k) == n0, "GMP merge duplicated Kaggle rows"

# ---------- 2) tracker-only rows (IPOs Kaggle does not have) ----------
un = pd.read_csv(GM / "gmp_unmatched_classified.csv", parse_dates=["listing_date"])
t = un[(un["category"] == "missing from base") & (un["issue_price"] > 0) & (un["listing_price_src"] > 0)]
t = pd.DataFrame({"listing_date": t["listing_date"], "company_name": t["company_name"],
                  "issue_size_cr": t["issue_size_cr"], "total_sub": t["total_sub"],
                  "issue_price": t["issue_price"], "listing_price": t["listing_price_src"],
                  "gmp_rs": t["gmp_rs"], "gmp_pct_of_issue": t["gmp_pct_of_issue"], "data_source": "tracker"})

df = pd.concat([k, t], ignore_index=True).sort_values("listing_date").reset_index(drop=True)
df["listing_year"] = df["listing_date"].dt.year
df["listing_gain_pct"] = (df["listing_price"] - df["issue_price"]) / df["issue_price"] * 100
df["listing_positive"] = (df["listing_gain_pct"] > 0).astype(int)

# ---------- 3) features: momentum (strictly earlier listings), market, size ----------
def momentum(n):
    mean, pos = [], []
    for d in df["listing_date"]:
        prior = df.loc[df["listing_date"] < d].tail(n)
        mean.append(prior["listing_gain_pct"].mean() if len(prior) >= 5 else np.nan)
        pos.append(prior["listing_positive"].mean() if len(prior) >= 5 else np.nan)
    return mean, pos
df["recent_gain_mean10"], df["recent_pos_rate10"] = momentum(10)
df["recent_gain_mean30"], _ = momentum(30)

def download(ticker, end):
    x = yf.download(ticker, start="2009-10-01", end=end, auto_adjust=False, progress=False)["Close"]
    return x.iloc[:, 0] if isinstance(x, pd.DataFrame) else x

mkt = pd.read_csv(MKT, index_col=0, parse_dates=True) if MKT.exists() else None
if mkt is None or mkt.index.max() < df["listing_date"].max() - pd.Timedelta(days=5):
    end = str((df["listing_date"].max() + pd.Timedelta(days=3)).date())
    mkt = pd.concat({"nifty": download("^NSEI", end), "vix": download("^INDIAVIX", end)}, axis=1)
    mkt.to_csv(MKT); print("Market data refreshed up to", mkt.index.max().date())
mkt.index = pd.to_datetime(mkt.index).tz_localize(None).astype("datetime64[ns]")
mkt = mkt.sort_index().dropna(subset=["nifty"]); mkt["vix"] = mkt["vix"].ffill()
mkt["nifty_ret_5d"] = mkt["nifty"].pct_change(5) * 100
mkt["nifty_ret_20d"] = mkt["nifty"].pct_change(20) * 100
mkt["vix_level"] = mkt["vix"]; mkt["vix_change_5d"] = mkt["vix"].pct_change(5) * 100
mkt.index.name = "mkt_date"
MC = ["nifty_ret_5d", "nifty_ret_20d", "vix_level", "vix_change_5d"]
df["listing_date"] = df["listing_date"].astype("datetime64[ns]")
df = pd.merge_asof(df, mkt[MC].reset_index(), left_on="listing_date", right_on="mkt_date",
                   direction="backward", allow_exact_matches=False)
stale = (df["listing_date"] - df["mkt_date"]).dt.days > 7
if stale.any():
    print(f"WARNING: {int(stale.sum())} rows have market data older than 7 days; those features are blanked")
    df.loc[stale, MC] = np.nan

df["log_issue_size"] = np.log(df["issue_size_cr"])
for c in ["qib", "nii", "retail", "total"]:
    col = f"{c}_sub"
    if col in df.columns:
        df[f"log_{c}"] = np.log1p(df[col])

out = df[df["listing_year"] >= 2017].copy()
out.to_csv(KG / "model_base_v2.csv", index=False)
print("Saved model_base_v2.csv:", len(out), "rows")
print(pd.crosstab(out["listing_year"], out["data_source"]))
print("\nGMP coverage by year:")
print(out.groupby("listing_year").agg(ipos=("listing_gain_pct", "size"),
                                      with_gmp=("gmp_pct_of_issue", lambda s: int(s.notna().sum()))))

# ---------- 4) small models, walk-forward, same rows for every comparison ----------
d = out[(out["listing_year"] >= 2020) & out["gmp_pct_of_issue"].notna()
        & out["log_total"].notna()].reset_index(drop=True)
M = ["nifty_ret_20d", "recent_gain_mean10"]
SETS = {"A  GMP only": ["gmp_pct_of_issue"],
        "B  GMP + total subscription": ["gmp_pct_of_issue", "log_total"],
        "C  B + size + market + momentum": ["gmp_pct_of_issue", "log_total", "log_issue_size"] + M,
        "D  C without GMP": ["log_total", "log_issue_size"] + M}

def clfs():
    return {"logreg": make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                                    LogisticRegression(max_iter=1000, class_weight="balanced")),
            "rf": make_pipeline(SimpleImputer(strategy="median"),
                                RandomForestClassifier(n_estimators=300, min_samples_leaf=5,
                                class_weight="balanced_subsample", random_state=42, n_jobs=-1))}

def walk(feats):
    outs = []
    for y in range(2022, 2027):
        tr, te = d[d["listing_year"] < y], d[d["listing_year"] == y].copy()
        if len(tr) < 40 or te.empty or tr["listing_positive"].nunique() < 2:
            continue
        for name, m in clfs().items():
            te[f"p_{name}"] = m.fit(tr[feats], tr["listing_positive"]).predict_proba(te[feats])[:, 1]
        r = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), Ridge(alpha=10.0))
        te["reg_ridge"] = r.fit(tr[feats], tr["listing_gain_pct"]).predict(te[feats])
        te["reg_median"] = tr["listing_gain_pct"].median()
        outs.append(te)
    return pd.concat(outs)

print(f"\nRows used: {len(d)} | test years 2022-2026")
rows, keep = [], {}
for label, feats in SETS.items():
    te = walk(feats); keep[label] = te
    y = te["listing_positive"]
    for name in ["logreg", "rf"]:
        p = te[f"p_{name}"]; yh = (p >= 0.5).astype(int)
        rows.append({"features": label, "model": name, "auc": roc_auc_score(y, p),
                     "acc": accuracy_score(y, yh),
                     "downside_recall": recall_score(y, yh, pos_label=0, zero_division=0),
                     "f1_negative": f1_score(y, yh, pos_label=0, zero_division=0)})
print(f"Test rows: {len(te)} | majority-class accuracy: {max(y.mean(), 1 - y.mean()):.3f}")
print(pd.DataFrame(rows).round(3).to_string(index=False))

te = keep["C  B + size + market + momentum"]
print("\nRegression MAE (percentage points):")
print(" predict median       :", round(mean_absolute_error(te["listing_gain_pct"], te["reg_median"]), 2))
print(" ridge (set C)        :", round(mean_absolute_error(te["listing_gain_pct"], te["reg_ridge"]), 2))
print(" gmp_pct as the guess :", round(mean_absolute_error(te["listing_gain_pct"], te["gmp_pct_of_issue"]), 2))
print("\nAUC by data source (set C, logreg):")
for s, grp in te.groupby("data_source"):
    if grp["listing_positive"].nunique() > 1:
        print(f"  {s:8s} n={len(grp):3d}  AUC={roc_auc_score(grp['listing_positive'], grp['p_logreg']):.3f}")