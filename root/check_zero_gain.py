import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.cleaning import DatasetManager

pd.set_option("display.width", 220); pd.set_option("display.max_columns", None)
dm = DatasetManager()
f, o = dm.load_dataset("ipo_features"), dm.load_dataset("ipo_outcomes")
d = f.merge(o[["ipo_id", "listing_open_price", "listing_gain_pct", "listing_positive"]], on="ipo_id")
d["listing_date"] = pd.to_datetime(d["listing_date"]); d["year"] = d["listing_date"].dt.year
d["gmp_pct"] = d["gmp"] / d["issue_price"] * 100
mb = pd.read_csv(ROOT / "data/interim/kaggle/model_base_v2.csv", parse_dates=["listing_date"])
d = d.merge(mb[["listing_date", "company_name", "data_source"]], on=["listing_date", "company_name"], how="left")
tr = pd.read_csv(ROOT / "data/interim/gmp/gmp_tracker_all_years.csv", parse_dates=["listing_date"])
tr["k"] = tr["issue_price"].round(2); d["k"] = d["issue_price"].round(2)
d = d.merge(tr[["listing_date", "k", "listing_price_src"]].drop_duplicates(["listing_date", "k"]),
            on=["listing_date", "k"], how="left")

z = d[d["listing_gain_pct"] == 0].copy()
print(f"Exactly-zero listings: {len(z)} of {len(d)} ({len(z)/len(d):.1%})")
print("\nBy year:\n", z.groupby("year").size().to_string())
print("\nBy data source:\n", z.groupby("data_source").size().to_string())
z["tracker_price_differs"] = (z["listing_price_src"].notna()
                              & ((z["listing_price_src"] - z["issue_price"]).abs() > 0.5))
print("\nZero-gain rows where the tracker lists a different price:", int(z["tracker_price_differs"].sum()),
      "| rows with no tracker price to compare:", int(z["listing_price_src"].isna().sum()))
z["date"] = z["listing_date"].dt.strftime("%Y-%m-%d")
cols = ["date", "company_name", "issue_price", "overall_subscription", "gmp_pct", "data_source",
        "listing_price_src", "tracker_price_differs"]
print("\nZero-gain rows with subscription >= 20x or GMP >= 10%:")
print(z[(z["overall_subscription"] >= 20) | (z["gmp_pct"] >= 10)][cols].to_string(index=False))
near = d[(d["listing_gain_pct"].abs() <= 2) & (d["listing_gain_pct"] != 0)]
print(f"\nNon-zero listings within +/-2%: {len(near)} | positive share: {near['listing_positive'].mean():.1%}")