from pathlib import Path
import pandas as pd

SRC = "E:/ipo-analyzer1/data/raw/Initial_Public_Offering_(Updated).xlsx"
OUT = Path("E:/ipo-analyzer1/data/interim/kaggle")
OUT.mkdir(parents=True, exist_ok=True)

df = pd.read_excel(SRC)
df = df.rename(columns={
    "Date": "listing_date", "IPO_Name": "company_name",
    "Issue_Size(crores)": "issue_size_cr",
    "QIB": "qib_sub", "HNI": "nii_sub", "RII": "retail_sub", "Total": "total_sub",
    "Offer Price": "issue_price", "List Price": "listing_price",
    "Listing Gain": "listing_gain_src",
})
df["listing_date"] = pd.to_datetime(df["listing_date"])
df["listing_year"] = df["listing_date"].dt.year

# Post-listing price columns are leakage: remove from the clean file
df = df.drop(columns=["CMP(BSE)", "CMP(NSE)", "Current Gains"])

# Target, recomputed from prices
df["listing_gain_pct"] = (df["listing_price"] - df["issue_price"]) / df["issue_price"] * 100
df["listing_positive"] = (df["listing_gain_pct"] > 0).astype(int)

# ---- Exclusion rules (hard) ----
name = df["company_name"].astype(str).str.lower()
reason = pd.Series("", index=df.index)

TRUNCATED_TRUSTS = ("bagmane", "citius transnet", "raajmarg","anantam highways", "knowledge realty")
is_trust = (name.str.contains(r"reit|invit|trust|fund|office parks|real estate", regex=True) | name.str.startswith(TRUNCATED_TRUSTS))
reason[is_trust] = "REIT/InvIT/trust (not an operating-company IPO)"
FPOS = [("power grid corporation", 2013), ("yes bank", 2020), ("vodafone idea", 2024)]
fpo = pd.Series(False, index=df.index)
for nm, yr in FPOS:
    fpo |= name.str.contains(nm, regex=False) & (df["listing_year"] == yr)
reason[fpo & (reason == "")] = "follow-on public offer (FPO), not an IPO"

bad_price = (df["issue_price"].isna() | df["listing_price"].isna()
             | (df["issue_price"] <= 0) | (df["listing_price"] <= 0))
reason[bad_price & (reason == "")] = "missing or invalid issue/listing price"

excluded = df[reason != ""].assign(exclusion_reason=reason[reason != ""])
kept = df[reason == ""].copy()

# ---- Review flags (soft; nothing removed) ----
kept["review_sme_suspect"] = (kept["listing_year"] >= 2012) & (kept["issue_size_cr"] < 100)
VERIFIED_MAINBOARD = ("likhitha infrastructure", "xelpmoc design", "dharan infra epc",
                      "astron paper", "salasar techno", "nmdc")
kept["segment_verified_mainboard"] = kept["company_name"].str.lower().str.startswith(VERIFIED_MAINBOARD)
kept["review_sme_suspect"] = kept["review_sme_suspect"] & ~kept["segment_verified_mainboard"]

kept["review_zero_retail"] = kept["retail_sub"].eq(0) | kept["retail_sub"].isna()
kept["review_duplicate_name"] = kept["company_name"].duplicated(keep=False)
kept["review_missing_subscription"] = kept[["qib_sub", "nii_sub", "retail_sub", "total_sub"]].isna().any(axis=1)
flags = [c for c in kept.columns if c.startswith("review_")]
review = kept[kept[flags].any(axis=1)]

kept.to_csv(OUT / "kaggle_clean_candidates.csv", index=False)
excluded.to_csv(OUT / "kaggle_excluded.csv", index=False)
review.to_csv(OUT / "kaggle_review_queue.csv", index=False)

pd.set_option("display.width", 200); pd.set_option("display.max_rows", 200)
print(f"Total: {len(df)} | kept: {len(kept)} | excluded: {len(excluded)} | in review queue: {len(review)}")
print("\nExcluded by reason:\n", excluded["exclusion_reason"].value_counts())
print("\nKept per year:\n", kept["listing_year"].value_counts().sort_index())
print("\nReview flag counts:\n", kept[flags].sum())
print("\nClass balance (kept):", kept["listing_positive"].mean().round(3))
print(kept["listing_gain_pct"].describe())
print("\nExcluded rows:\n", excluded[["listing_date", "company_name", "exclusion_reason"]].to_string())
print("\nDuplicate names:\n", kept.loc[kept["review_duplicate_name"], ["listing_date", "company_name"]])






















