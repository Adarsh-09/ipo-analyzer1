import re, sys
from difflib import SequenceMatcher
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "root"))
from parse_gmp_tracker import parse_tracker_html

KG, GM, RAW = ROOT / "data/interim/kaggle", ROOT / "data/interim/gmp", ROOT / "data/raw"
pd.set_option("display.width", 220); pd.set_option("display.max_columns", None); pd.set_option("display.max_rows", 200)

NON_EQUITY = r"\breit\b|invit|\btrust\b|real estate|propshare|property share|office parks|infrastructure fund"
TRUNCATED = ("bagmane", "citius transnet", "raajmarg", "anantam highways", "knowledge realty")
FPOS = [("power grid corporation", 2013), ("yes bank", 2020), ("vodafone idea", 2024)]

def exclusion_reason(df):
    n = df["company_name"].str.lower().str.strip(); yr = df["listing_date"].dt.year
    r = pd.Series("", index=df.index)
    r[n.str.contains(NON_EQUITY, regex=True) | n.str.startswith(TRUNCATED)] = "non-equity unit (REIT/InvIT/SM-REIT)"
    r[(df["issue_price"] > 10000) & (r == "")] = "unit price above 10,000 (not an equity IPO)"
    fpo = (n == "vi") & (yr == 2024)
    for nm, y in FPOS:
        fpo |= n.str.contains(nm, regex=False) & (yr == y)
    r[fpo & (r == "")] = "follow-on public offer (FPO)"
    r[(df["issue_price"].isna() | (df["issue_price"] <= 0)) & (r == "")] = "invalid issue price"
    return r

# ---------- 1) Kaggle rows ----------
k = pd.read_csv(KG / "kaggle_clean_candidates.csv", parse_dates=["listing_date"])
k["data_source"] = "kaggle"
rk = exclusion_reason(k)
removed = [k[rk != ""].assign(reason=rk[rk != ""], source="kaggle")]
k = k[rk == ""].reset_index(drop=True)
k["kid"] = np.arange(len(k)); k["issue_price_r"] = k["issue_price"].round(2)

# ---------- 2) tracker rows, parsed from cached pages (no de-duplication on price) ----------
t = pd.concat([parse_tracker_html((RAW / "gmp" / f"tracker_{y}.html").read_text(encoding="utf-8", errors="ignore"), y)
               for y in range(2020, 2027)], ignore_index=True)
t = t.drop_duplicates(["listing_date", "company_name", "issue_price"]).reset_index(drop=True)
t["tid"] = np.arange(len(t)); t["issue_price_r"] = t["issue_price"].round(2)
rt = exclusion_reason(t)
removed.append(t[rt != ""].assign(reason=rt[rt != ""], source="tracker"))
t = t[rt == ""].copy()

# ---------- 3) match Kaggle <-> tracker: same date + price, then name/size to choose ----------
def name_key(s):
    s = re.sub(r"\.\.\.$", "", str(s).lower())
    s = re.sub(r"\b(limited|ltd|private|pvt)\b", "", s)
    return re.sub(r"[^a-z0-9]", "", s)

def sim(a, b):
    a, b = name_key(a), name_key(b); n = min(len(a), len(b), 15)
    return SequenceMatcher(None, a[:n], b[:n]).ratio() if n else 0.0

cand = k[["kid", "company_name", "listing_date", "issue_price_r", "issue_size_cr", "total_sub"]].merge(
    t[["tid", "company_name", "listing_date", "issue_price_r", "issue_size_cr", "total_sub",
       "gmp_rs", "gmp_pct_of_issue", "listing_price_src", "symbol"]],
    on=["listing_date", "issue_price_r"], suffixes=("", "_t"))
cand["name_sim"] = [sim(a, b) for a, b in zip(cand["company_name"], cand["company_name_t"])]
cand["size_diff"] = ((cand["issue_size_cr"] - cand["issue_size_cr_t"]).abs() / cand["issue_size_cr"]).fillna(1)
cand["ok"] = (cand["name_sim"] >= 0.6) | (cand["size_diff"] <= 0.10)
cand["score"] = cand["name_sim"] - cand["size_diff"].clip(upper=1)
best = (cand[cand["ok"]].sort_values("score", ascending=False)
        .drop_duplicates("kid").drop_duplicates("tid"))          # one tracker row per Kaggle row, and vice versa
cand.assign(accepted=cand["kid"].isin(best["kid"]) & cand["tid"].isin(best["tid"])).to_csv(GM / "join_audit_v3.csv", index=False)

n0 = len(k)
k = k.merge(best[["kid", "tid", "gmp_rs", "gmp_pct_of_issue", "symbol", "total_sub_t"]], on="kid", how="left")
assert len(k) == n0 and k["tid"].dropna().is_unique
rel = ((k["total_sub"] - k["total_sub_t"]).abs() / k["total_sub"]).replace([np.inf], 1.0).fillna(0)
k["sub_conflict"] = rel > 0.25
k.loc[k["sub_conflict"], "total_sub"] = k.loc[k["sub_conflict"], "total_sub_t"]
k.loc[k["sub_conflict"], ["qib_sub", "nii_sub", "retail_sub"]] = np.nan
k = k.drop(columns=["total_sub_t"])

# ---------- 4) tracker-only rows: never add an IPO whose date+price already exists in Kaggle ----------
left = t[~t["tid"].isin(best["tid"])]
k_keys = set(zip(k["listing_date"], k["issue_price_r"]))
in_k = np.array([(d, p) in k_keys for d, p in zip(left["listing_date"], left["issue_price_r"])])
rejected = left[in_k]
new = left[~in_k]
new = new[(new["issue_price"] > 0) & (new["listing_price_src"] > 0)]
new = pd.DataFrame({"listing_date": new["listing_date"], "company_name": new["company_name"],
                    "issue_size_cr": new["issue_size_cr"], "total_sub": new["total_sub"],
                    "issue_price": new["issue_price"], "listing_price": new["listing_price_src"],
                    "gmp_rs": new["gmp_rs"], "gmp_pct_of_issue": new["gmp_pct_of_issue"],
                    "symbol": new["symbol"], "tid": new["tid"], "data_source": "tracker"})

# ---------- 5) combine, deterministic order, targets, features ----------
df = pd.concat([k.drop(columns=["kid", "issue_price_r"]), new], ignore_index=True)
df["listing_date"] = pd.to_datetime(df["listing_date"]).astype("datetime64[ns]")
df = df.sort_values(["listing_date", "company_name", "issue_price"], kind="stable").reset_index(drop=True)
df["listing_year"] = df["listing_date"].dt.year
df["sub_conflict"] = (df["sub_conflict"].infer_objects(copy=False).fillna(False).astype(bool))
df["listing_gain_pct"] = (df["listing_price"] - df["issue_price"]) / df["issue_price"] * 100
df["listing_positive"] = (df["listing_gain_pct"] > 0).astype(int)
df["gmp_missing"] = df["gmp_pct_of_issue"].isna().astype(int)

def momentum(n):
    mean, pos = [], []
    for d in df["listing_date"]:
        prior = df.loc[df["listing_date"] < d].tail(n)
        mean.append(prior["listing_gain_pct"].mean() if len(prior) >= 5 else np.nan)
        pos.append(prior["listing_positive"].mean() if len(prior) >= 5 else np.nan)
    return mean, pos
df["recent_gain_mean10"], df["recent_pos_rate10"] = momentum(10)
df["recent_gain_mean30"], _ = momentum(30)

mkt = pd.read_csv(RAW / "market_context.csv", index_col=0, parse_dates=True)
if mkt.index.max() < df["listing_date"].max() - pd.Timedelta(days=5):
    raise SystemExit("Market cache is older than the newest listing; run build_v2.py once to refresh it")
mkt.index = pd.to_datetime(mkt.index).tz_localize(None).astype("datetime64[ns]")
mkt = mkt.sort_index().dropna(subset=["nifty"]); mkt["vix"] = mkt["vix"].ffill()
mkt["nifty_ret_5d"] = mkt["nifty"].pct_change(5) * 100
mkt["nifty_ret_20d"] = mkt["nifty"].pct_change(20) * 100
mkt["vix_level"] = mkt["vix"]; mkt["vix_change_5d"] = mkt["vix"].pct_change(5) * 100
mkt.index.name = "mkt_date"
MC = ["nifty_ret_5d", "nifty_ret_20d", "vix_level", "vix_change_5d"]
df = pd.merge_asof(df, mkt[MC].reset_index(), left_on="listing_date", right_on="mkt_date",
                   direction="backward", allow_exact_matches=False)
stale = (df["listing_date"] - df["mkt_date"]).dt.days > 7
df.loc[stale, MC] = np.nan
df["log_issue_size"] = np.log(df["issue_size_cr"])
for c in ["qib", "nii", "retail", "total"]:
    df[f"log_{c}"] = np.log1p(df[f"{c}_sub"])

out = df[df["listing_year"] >= 2017].copy()
assert not out.duplicated(["listing_date", "company_name", "issue_price"]).any()
out.to_csv(KG / "model_base_v3.csv", index=False)

# ---------- 6) report ----------
rem = pd.concat(removed)
print("Rows removed by rule:\n", rem.groupby(["source", "reason"]).size().to_string())
print("\nNon-equity units still found in either source (review):")
print(rem[rem["reason"].str.startswith(("non-equity", "unit price"))][["listing_date", "company_name", "issue_price", "source"]]
      .assign(listing_date=lambda x: x["listing_date"].dt.strftime("%Y-%m-%d")).to_string(index=False))
print(f"\nModel base v3: {len(out)} rows (v2 had 557) | positive {out['listing_positive'].mean():.1%} | "
      f"GMP present {int(out['gmp_pct_of_issue'].notna().sum())}")
print(pd.crosstab(out["listing_year"], out["data_source"]))

shared = t[t.duplicated(["listing_date", "issue_price_r"], keep=False)][["listing_date", "issue_price_r"]].drop_duplicates()
print(f"\nTracker keys shared by more than one IPO: {len(shared)}")
print(best.merge(shared, on=["listing_date", "issue_price_r"])
      [["listing_date", "company_name", "company_name_t", "issue_size_cr", "issue_size_cr_t", "gmp_pct_of_issue"]].to_string(index=False))
print(f"\nDate+price candidates rejected on name/size: {int((~cand['ok']).sum())} | "
      f"tracker rows with a Kaggle key but no accepted match (not added): {len(rejected)}")
acc = best.assign(sub_diff=((best["total_sub"] - best["total_sub_t"]).abs() / best["total_sub"]).fillna(0))
flag = acc[(acc["size_diff"] > 0.10) | (acc["sub_diff"] > 0.25)]
print(f"Accepted matches where issue size differs >10% or subscription differs >25%: {len(flag)}")
print(f"  tracker subscription higher than Kaggle in {(flag['total_sub_t'] > flag['total_sub']).mean():.0%} of them | rows marked sub_conflict: {int(out['sub_conflict'].sum())}")
print(flag[["listing_date", "company_name", "company_name_t", "issue_size_cr", "issue_size_cr_t", "total_sub", "total_sub_t"]].head(15).to_string(index=False))
gain = out["listing_gain_pct"]
print(f"\nExactly flat: {int((gain == 0).sum())} | within +/-2%: {int((gain.abs() <= 2).sum())}")