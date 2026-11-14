import re, sys
from collections import Counter
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.cleaning import (validate_features_dataset, validate_outcomes_dataset,
                          validate_registry_dataset, validate_feature_sources_dataset)

STG = ROOT / "data/interim/processed_staging"
KAGGLE_URL = ""        # paste the Kaggle dataset URL here when you have it
TRACKER_URL = "https://www.investorgain.com/report/ipo-gmp-performance-tracker/377/ipo/"
RETRIEVED = "2026-11-14"

reg = pd.read_csv(STG / "ipo_registry.csv"); fea = pd.read_csv(STG / "ipo_features.csv")
out = pd.read_csv(STG / "ipo_outcomes.csv"); tags = pd.read_csv(STG / "ipo_source_tags.csv")

def counts(rep):
    ec = rep.error_count() if callable(rep.error_count) else rep.error_count
    wc = rep.warning_count() if callable(rep.warning_count) else rep.warning_count
    issues = getattr(rep, "issues", None)
    if issues is None:
        issues = rep.to_dict().get("issues", [])
    return ec, wc, [str(i) for i in issues]

print("Report structure:", {k: (len(v) if hasattr(v, "__len__") and not isinstance(v, str) else v)
                            for k, v in validate_outcomes_dataset(out).to_dict().items()})

# ---------- 1) do the validators catch bad data? ----------
print("\nNegative tests (each should show errors > 0):")
def trial(label, fn, df):
    ec, wc, msgs = counts(fn(df))
    print(f"  {label:52s} errors={ec:3d} warnings={wc:3d}  {(msgs[0][:100] if msgs else 'NOT CAUGHT')}")

f = fea.copy(); f.loc[0, ["prediction_stage", "overall_subscription"]] = ["pre_close", 5.0]
trial("pre_close row carrying a subscription value", validate_features_dataset, f)
f = fea.copy(); i = f.index[f["gmp"].notna()][0]; f.loc[i, ["gmp", "gmp_missing"]] = [np.nan, 0]
trial("GMP blank but gmp_missing = 0", validate_features_dataset, f)
f = fea.copy(); i = f.index[f["gmp"].isna()][0]; f.loc[i, ["gmp", "gmp_missing"]] = [0.0, 1]
trial("GMP set to 0.0 where it was missing", validate_features_dataset, f)
f = fea.copy(); f.loc[2, "issue_price"] = -5
trial("negative issue price", validate_features_dataset, f)
o = out.copy(); o.loc[0, "listing_gain_pct"] += 10
trial("listing_gain_pct inconsistent with prices", validate_outcomes_dataset, o)
o = out.copy(); o.loc[0, "listing_positive"] = 1 - o.loc[0, "listing_positive"]
trial("listing_positive contradicts the gain", validate_outcomes_dataset, o)
r = reg.copy(); r.loc[1, "ipo_id"] = r.loc[0, "ipo_id"]
trial("duplicate ipo_id in registry", validate_registry_dataset, r)
r = reg.copy(); r.loc[0, "ipo_id"] = "BAD-ID"
trial("malformed ipo_id", validate_registry_dataset, r)

# ---------- 2) provenance table (one row per sourced value) ----------
fs = fea.merge(tags, on="ipo_id")
SPEC = ["issue_price", "issue_size_cr", "overall_subscription", "qib_subscription",
        "nii_subscription", "retail_subscription", "gmp"]
parts = []
for feat in SPEC:
    s = fs[fs[feat].notna()]
    from_tracker = (s["data_source"] == "tracker") | (feat == "gmp")
    parts.append(pd.DataFrame({
        "ipo_id": s["ipo_id"], "prediction_stage": s["prediction_stage"], "data_cutoff": s["data_cutoff"],
        "feature_name": feat, "feature_value": s[feat].astype(str),
        "source_name": np.where(from_tracker, "InvestorGain GMP Performance Tracker",
                                "Kaggle: Initial_Public_Offering_(Updated).xlsx"),
        "source_url": np.where(from_tracker, TRACKER_URL, KAGGLE_URL or None),
        "document_name": None, "document_page": None, "retrieved_at": RETRIEVED,
        "verification_status": "unverified",
        "notes": "aggregator value; not checked against the RHP or an exchange filing"}))
src = pd.concat(parts, ignore_index=True)
src.to_csv(STG / "ipo_feature_sources.csv", index=False)
ec, wc, msgs = counts(validate_feature_sources_dataset(src))
print(f"\nipo_feature_sources: {len(src)} rows | {ec} errors, {wc} warnings")
for msg, n in Counter(re.sub(r"INMAIN-\d{4}-\d{4}", "<id>", m)[:170] for m in msgs).most_common(10):
    print(f"  {n:5d} x {msg}")

# ---------- 3) the real tables once more, counted directly ----------
for name, fn, df in [("registry", validate_registry_dataset, reg), ("outcomes", validate_outcomes_dataset, out),
                     ("features", validate_features_dataset, fea)]:
    ec, wc, _ = counts(fn(df)); print(f"{name}: {ec} errors, {wc} warnings")