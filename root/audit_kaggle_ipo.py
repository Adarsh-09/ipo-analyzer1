from pathlib import Path
import pandas as pd

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", 100)

PATH = "E:/ipo-analyzer1/data/raw/Initial_Public_Offering_(Updated).xlsx"
OUT = Path("data/interim/kaggle_audit_flags.csv")
OUT.parent.mkdir(parents=True, exist_ok=True)

df = pd.read_excel(PATH)
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

print("Rows:", len(df))
print("Date range:", df["Date"].min(), "->", df["Date"].max(), "| unparseable dates:", df["Date"].isna().sum())
print("\nRows per year:\n", df["Date"].dt.year.value_counts().sort_index())

print("\nDuplicate IPO names:", df["IPO_Name"].duplicated().sum())
print("Duplicate name+date:", df.duplicated(["IPO_Name", "Date"]).sum())

# Recompute the target from prices
df["gain_recalc"] = (df["List Price"] - df["Offer Price"]) / df["Offer Price"] * 100
diff = (df["gain_recalc"] - df["Listing Gain"]).abs()
print("\nListing Gain mismatches (>0.15 pts):", int((diff > 0.15).sum()))
print(df.loc[diff > 0.15, ["IPO_Name", "Offer Price", "List Price", "Listing Gain", "gain_recalc"]])

# Flags for non-company-IPO or suspicious rows (flags only, nothing is dropped)
name = df["IPO_Name"].astype(str).str.lower()
df["flag_reit_invit_name"] = name.str.contains("reit|invit|trust|real estate invest|infrastructure invest", regex=True)
df["flag_zero_retail"] = df["RII"].eq(0)
df["flag_price_100"] = df["Offer Price"].eq(100)
df["flag_small_issue"] = df["Issue_Size(crores)"] < 50
df["flag_missing_core"] = df[["Total", "List Price", "Offer Price"]].isna().any(axis=1)

flag_cols = [c for c in df.columns if c.startswith("flag_")]
print("\nFlag counts:\n", df[flag_cols].sum())

print("\nIssue size (crores):\n", df["Issue_Size(crores)"].describe())

pos = (df["List Price"] > df["Offer Price"])
print("\nPositive listing share:", round(pos.mean(), 3))
print("Listing gain %:\n", df["gain_recalc"].describe())

print("\nFlagged REIT/InvIT-like rows:")
print(df.loc[df["flag_reit_invit_name"] | (df["flag_zero_retail"] & df["flag_price_100"]),
             ["Date", "IPO_Name", "Issue_Size(crores)", "RII", "Offer Price"]])

df[df[flag_cols].any(axis=1)].to_csv(OUT, index=False)
print("\nSaved flagged rows to", OUT)