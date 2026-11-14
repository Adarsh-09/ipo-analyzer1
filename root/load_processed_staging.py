import re, sys
from collections import Counter
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.cleaning import (format_ipo_id, validate_features_dataset,
                          validate_outcomes_dataset, validate_registry_dataset)

KG, GM = ROOT / "data/interim/kaggle", ROOT / "data/interim/gmp"
STG = ROOT / "data/interim/processed_staging"; STG.mkdir(parents=True, exist_ok=True)

b = pd.read_csv(KG / "model_base_v2.csv", parse_dates=["listing_date"])
g = pd.read_csv(GM / "gmp_tracker_all_years.csv", parse_dates=["listing_date"])
g["issue_price_r"] = g["issue_price"].round(2); b["issue_price_r"] = b["issue_price"].round(2)
sym = g.drop_duplicates(["listing_date", "issue_price_r"])[["listing_date", "issue_price_r", "symbol"]]
n0 = len(b)
b = b.merge(sym, on=["listing_date", "issue_price_r"], how="left")
assert len(b) == n0

# ---- deterministic IDs: INMAIN-<listing year>-<sequence> ----
b = b.sort_values(["listing_date", "company_name"]).reset_index(drop=True)
yr = b["listing_date"].dt.year
b["ipo_id"] = [format_ipo_id(int(y), int(s)) for y, s in zip(yr, b.groupby(yr).cumcount() + 1)]
assert b["ipo_id"].is_unique
ld = b["listing_date"].dt.strftime("%Y-%m-%d")
cutoff = (b["listing_date"] - pd.Timedelta(days=1)).dt.strftime("%Y-%m-%d")
has_gmp = b["gmp_rs"].notna()

registry = pd.DataFrame({"ipo_id": b["ipo_id"], "company_name": b["company_name"], "symbol": b["symbol"],
                         "issue_open_date": np.nan, "issue_close_date": np.nan, "listing_date": ld})

features = pd.DataFrame({
    "ipo_id": b["ipo_id"], "company_name": b["company_name"], "symbol": b["symbol"], "exchange": np.nan,
    "issue_open_date": np.nan, "issue_close_date": np.nan, "issue_price": b["issue_price"],
    "price_band_low": np.nan, "price_band_high": np.nan, "issue_size_cr": b["issue_size_cr"],
    "fresh_issue_cr": np.nan, "ofs_cr": np.nan, "listing_date": ld,
    "revenue": np.nan, "revenue_period": np.nan, "profit_after_tax": np.nan, "pat_period": np.nan,
    "ebitda": np.nan, "ebitda_period": np.nan, "total_debt": np.nan, "net_worth": np.nan,
    "cash_flow_from_operations": np.nan, "eps": np.nan, "nav": np.nan, "pe_ratio": np.nan,
    "pb_ratio": np.nan, "peer_pe_ratio": np.nan, "peer_pb_ratio": np.nan,
    "qib_subscription": b["qib_sub"], "nii_subscription": b["nii_sub"],
    "retail_subscription": b["retail_sub"], "overall_subscription": b["total_sub"],
    "gmp": b["gmp_rs"], "gmp_change": np.nan,
    "gmp_source": np.where(has_gmp, "InvestorGain GMP Performance Tracker (final value)", None),
    "gmp_recorded_at": np.nan, "gmp_missing": (~has_gmp).astype(int),
    "prediction_stage": "post_close", "data_cutoff": cutoff})

outcomes = pd.DataFrame({"ipo_id": b["ipo_id"], "listing_date": ld, "issue_price": b["issue_price"],
                         "listing_open_price": b["listing_price"], "listing_close_price": np.nan,
                         "listing_gain_pct": b["listing_gain_pct"], "listing_positive": b["listing_positive"]})

# provenance kept alongside for the feature-sources table later
b[["ipo_id", "data_source"]].to_csv(STG / "ipo_source_tags.csv", index=False)
for name, df in [("ipo_registry", registry), ("ipo_features", features), ("ipo_outcomes", outcomes)]:
    df.to_csv(STG / f"{name}.csv", index=False)
print("Staged:", {n: len(d) for n, d in [("registry", registry), ("features", features), ("outcomes", outcomes)]})

def show(name, rep, top=12):
    ec, wc = rep.error_count, rep.warning_count
    ec = ec() if callable(ec) else ec; wc = wc() if callable(wc) else wc
    print(f"\n=== {name}: {ec} errors, {wc} warnings ===")
    issues = getattr(rep, "issues", None)
    if issues is None:
        issues = rep.to_dict().get("issues", [])
    c = Counter(re.sub(r"INMAIN-\d{4}-\d{4}", "<id>", str(i))[:180] for i in issues)
    for msg, n in c.most_common(top):
        print(f"  {n:4d} x {msg}")

show("registry", validate_registry_dataset(registry))
show("outcomes", validate_outcomes_dataset(outcomes))
show("features", validate_features_dataset(features))