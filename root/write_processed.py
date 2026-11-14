import shutil, sys
from datetime import datetime
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.cleaning import DatasetManager, check_referential_integrity

STG = ROOT / "data/interim/processed_staging"
NAMES = ["ipo_registry", "ipo_features", "ipo_outcomes", "ipo_feature_sources"]
dm = DatasetManager()
frames = {n: pd.read_csv(STG / f"{n}.csv", dtype={"ipo_id": str, "symbol": str, "company_name": str})
          for n in NAMES}

def summarize(name, rep, top=8):
    print(f"{name:22s} rows={rep.total_records:5d} valid={rep.is_valid} "
          f"errors={rep.error_count} warnings={rep.warning_count}")
    for issue in (list(rep.errors) + list(rep.warnings))[:top]:
        print("     ", issue)

# ---------- 1) full validation before anything is written ----------
problems = 0
for n in NAMES:
    rep = dm.validate_dataset(n, frames[n]); summarize(n, rep)
    dups = dm.check_duplicates(n, frames[n]); print(f"{'':22s} duplicates on default keys: {len(dups)}")
    problems += rep.error_count + len(dups)

ri = check_referential_integrity(frames["ipo_features"], frames["ipo_outcomes"], None, frames["ipo_registry"])
print("\nReferential-integrity issues:", len(ri)); problems += len(ri)
ids = {n: set(frames[n]["ipo_id"]) for n in NAMES}
same = ids["ipo_registry"] == ids["ipo_features"] == ids["ipo_outcomes"]
print("Registry / features / outcomes cover identical IDs:", same)
print("Provenance IDs all in registry:", ids["ipo_feature_sources"] <= ids["ipo_registry"])
problems += int(not same) + int(not ids["ipo_feature_sources"] <= ids["ipo_registry"])

if problems:
    sys.exit(f"\nSTOPPED: {problems} problem(s). Nothing was written to data/processed/.")

# ---------- 2) back up, then write atomically through DatasetManager ----------
bk = ROOT / "data/interim" / f"processed_backup_{datetime.now():%Y%m%d_%H%M%S}"
bk.mkdir(parents=True)
for f in (ROOT / "data/processed").glob("*.csv"):
    shutil.copy(f, bk / f.name)
print("\nBackup of previous files:", bk)
for n in NAMES:
    print("wrote", dm.save_dataset(frames[n], n))

# ---------- 3) reload and re-validate (round trip) ----------
print("\nRound trip:")
for n in NAMES:
    back = dm.load_dataset(n); rep = dm.validate_dataset(n, back)
    print(f"  {n:22s} rows={len(back):5d} errors={rep.error_count} warnings={rep.warning_count}")

res = dm.generate_data_quality_report()
print("\nData-quality report:", res["report_file"])

# ---------- 4) quick facts about what is now in the processed store ----------
o, f = dm.load_dataset("ipo_outcomes"), dm.load_dataset("ipo_features")
print("\nIPOs per listing year:\n", o["listing_date"].str[:4].value_counts().sort_index().to_string())
print(f"\nPositive listings: {o['listing_positive'].mean():.1%} | GMP present: {int((f['gmp_missing'] == 0).sum())} of {len(f)}")