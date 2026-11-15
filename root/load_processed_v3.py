import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.cleaning import (DatasetManager, format_ipo_id, parse_ipo_id, validate_feature_sources_dataset,
                          validate_features_dataset, validate_outcomes_dataset, validate_registry_dataset)

KG = ROOT / "data/interim/kaggle"
STG = ROOT / "data/interim/processed_staging"; STG.mkdir(parents=True, exist_ok=True)
TRACKER_URL = "https://www.investorgain.com/report/ipo-gmp-performance-tracker/377/ipo/"
KAGGLE_URL = ""          # add the Kaggle dataset URL when you have it
RETRIEVED = "2026-11-15"

b = pd.read_csv(KG / "model_base_v3.csv", parse_dates=["listing_date"])
b = b.sort_values(["listing_date", "company_name", "issue_price"], kind="stable").reset_index(drop=True)
if "sub_conflict" not in b.columns:
    b["sub_conflict"] = False
b["sub_conflict"] = b["sub_conflict"].astype(bool)

# ---------- stable IDs: keep existing, assign new ones after the highest used, never reuse ----------
dm = DatasetManager()
old = dm.load_dataset("ipo_registry")
old_map, next_seq = {}, {}
for r in old.itertuples():
    old_map[(str(r.listing_date)[:10], r.company_name)] = r.ipo_id
    _, y, s = parse_ipo_id(r.ipo_id)
    next_seq[y] = max(next_seq.get(y, 0), s)
ids, new_ids = [], 0
for r in b.itertuples():
    key = (r.listing_date.strftime("%Y-%m-%d"), r.company_name)
    if key in old_map:
        ids.append(old_map[key])
    else:
        y = r.listing_date.year
        next_seq[y] = next_seq.get(y, 0) + 1
        ids.append(format_ipo_id(y, next_seq[y])); new_ids += 1
b["ipo_id"] = ids
assert b["ipo_id"].is_unique
print(f"IDs kept: {len(b) - new_ids} | new: {new_ids} | retired, not reused: {sorted(set(old_map.values()) - set(ids))}")

ld = b["listing_date"].dt.strftime("%Y-%m-%d")
cutoff = (b["listing_date"] - pd.Timedelta(days=1)).dt.strftime("%Y-%m-%d")
has_gmp = b["gmp_rs"].notna()

registry = pd.DataFrame({"ipo_id": b["ipo_id"], "company_name": b["company_name"], "symbol": b["symbol"],
                         "issue_open_date": np.nan, "issue_close_date": np.nan, "listing_date": ld})
cols = ["exchange", "issue_open_date", "issue_close_date", "price_band_low", "price_band_high", "fresh_issue_cr",
        "ofs_cr", "revenue", "revenue_period", "profit_after_tax", "pat_period", "ebitda", "ebitda_period",
        "total_debt", "net_worth", "cash_flow_from_operations", "eps", "nav", "pe_ratio", "pb_ratio",
        "peer_pe_ratio", "peer_pb_ratio", "gmp_change", "gmp_recorded_at"]
features = pd.DataFrame({"ipo_id": b["ipo_id"], "company_name": b["company_name"], "symbol": b["symbol"],
                         "issue_price": b["issue_price"], "issue_size_cr": b["issue_size_cr"], "listing_date": ld,
                         "qib_subscription": b["qib_sub"], "nii_subscription": b["nii_sub"],
                         "retail_subscription": b["retail_sub"], "overall_subscription": b["total_sub"],
                         "gmp": b["gmp_rs"],
                         "gmp_source": np.where(has_gmp, "InvestorGain GMP Performance Tracker (final value)", None),
                         "gmp_missing": (~has_gmp).astype(int), "prediction_stage": "listing_eve",
                         "data_cutoff": cutoff})
for c in cols:
    features[c] = np.nan
features = features[["ipo_id", "company_name", "symbol", "exchange", "issue_open_date", "issue_close_date",
                     "issue_price", "price_band_low", "price_band_high", "issue_size_cr", "fresh_issue_cr", "ofs_cr",
                     "listing_date", "revenue", "revenue_period", "profit_after_tax", "pat_period", "ebitda",
                     "ebitda_period", "total_debt", "net_worth", "cash_flow_from_operations", "eps", "nav",
                     "pe_ratio", "pb_ratio", "peer_pe_ratio", "peer_pb_ratio", "qib_subscription", "nii_subscription",
                     "retail_subscription", "overall_subscription", "gmp", "gmp_change", "gmp_source",
                     "gmp_recorded_at", "gmp_missing", "prediction_stage", "data_cutoff"]]
outcomes = pd.DataFrame({"ipo_id": b["ipo_id"], "listing_date": ld, "issue_price": b["issue_price"],
                         "listing_open_price": b["listing_price"], "listing_close_price": np.nan,
                         "listing_gain_pct": b["listing_gain_pct"], "listing_positive": b["listing_positive"]})

# ---------- provenance: one row per sourced value ----------
parts = []
for feat, col in [("issue_price", "issue_price"), ("issue_size_cr", "issue_size_cr"),
                  ("overall_subscription", "total_sub"), ("qib_subscription", "qib_sub"),
                  ("nii_subscription", "nii_sub"), ("retail_subscription", "retail_sub"), ("gmp", "gmp_rs")]:
    s = b[b[col].notna()]
    tracker = (s["data_source"] == "tracker") | (feat == "gmp") | ((feat == "overall_subscription") & s["sub_conflict"])
    swapped = (feat == "overall_subscription") & s["sub_conflict"]
    parts.append(pd.DataFrame({
        "ipo_id": s["ipo_id"], "prediction_stage": "listing_eve",
        "data_cutoff": (s["listing_date"] - pd.Timedelta(days=1)).dt.strftime("%Y-%m-%d"),
        "feature_name": feat, "feature_value": s[col].astype(str),
        "source_name": np.where(tracker, "InvestorGain GMP Performance Tracker", "Kaggle: Initial_Public_Offering_(Updated).xlsx"),
        "source_url": np.where(tracker, TRACKER_URL, KAGGLE_URL or None),
        "document_name": None, "document_page": None, "retrieved_at": RETRIEVED, "verification_status": "unverified",
        "notes": np.where(swapped, "tracker value used; Kaggle total subscription differed by more than 25%",
                          "aggregator value; not checked against the RHP or an exchange filing")}))
sources = pd.concat(parts, ignore_index=True)

for name, df in [("ipo_registry", registry), ("ipo_features", features), ("ipo_outcomes", outcomes),
                 ("ipo_feature_sources", sources)]:
    df.to_csv(STG / f"{name}.csv", index=False)

def show(name, rep, top=8):
    print(f"{name:22s} rows={rep.total_records:5d} errors={rep.error_count} warnings={rep.warning_count}")
    for issue in (list(rep.errors) + list(rep.warnings))[:top]:
        print("     ", issue)

print(f"\nStaged {len(registry)} IPOs | stage counts: {features['prediction_stage'].value_counts().to_dict()}")
show("registry", validate_registry_dataset(registry)); show("outcomes", validate_outcomes_dataset(outcomes))
show("features", validate_features_dataset(features)); show("feature_sources", validate_feature_sources_dataset(sources))