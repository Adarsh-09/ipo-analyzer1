import re, sys
from pathlib import Path
import pandas as pd
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "root"))
from src.collection.http_client import IPOHttpClient
from parse_gmp_tracker import parse_tracker_html

pd.set_option("display.width", 220); pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", 200)
URL = "https://www.investorgain.com/report/ipo-gmp-performance-tracker/377/ipo/"
GM, RAW = ROOT / "data/interim/gmp", ROOT / "data/raw/gmp"

g = pd.read_csv(GM / "gmp_tracker_all_years.csv", parse_dates=["listing_date"])
base = pd.read_csv(ROOT / "data/interim/kaggle/model_base_gmp.csv", parse_dates=["listing_date"])
base["issue_price_r"] = base["issue_price"].round(2)
g["issue_price_r"] = g["issue_price"].round(2)

print("Tracker rows per year (cap check):")
print(g.groupby("source_year")["listing_date"].agg(rows="size", first="min", last="max"))

# ---- 1) classify the tracker rows that did not match the base ----
key = set(zip(base["listing_date"], base["issue_price_r"]))
un = g[[(d, p) not in key for d, p in zip(g["listing_date"], g["issue_price_r"])]].copy()
trust = un["company_name"].str.contains(r"reit|invit|trust|fund|real estate", case=False, regex=True) \
        | un["company_name"].str.lower().isin(["vi", "yes bank"])

def near(r):
    tok = re.sub(r"[^a-z0-9 ]", "", r["company_name"].lower()).split()
    if not tok:
        return False
    sub = base[(base["listing_date"] - r["listing_date"]).abs() <= pd.Timedelta(days=5)]
    return bool(sub["company_name"].str.lower().str.startswith(tok[0]).any())

un["category"] = "missing from base"
un.loc[un.apply(near, axis=1), "category"] = "in base, date/price mismatch"
un.loc[trust, "category"] = "REIT/InvIT/FPO (correctly excluded)"
un["before_2017"] = un["listing_date"] < "2017-01-01"
print("\nUnmatched tracker rows by category and year:")
print(pd.crosstab(un["source_year"], un["category"]))
un.to_csv(GM / "gmp_unmatched_classified.csv", index=False)
print("\nMissing-from-base rows after Kaggle's last date (", base["listing_date"].max().date(), "):",
      int(((un["category"] == "missing from base") & (un["listing_date"] > base["listing_date"].max())).sum()))
print(un.loc[un["category"] == "in base, date/price mismatch",
             ["listing_date", "company_name", "issue_price"]].head(15).to_string())

# ---- 2) does the tracker's listing price agree with Kaggle's? ----
mm = base[["listing_date", "issue_price_r", "listing_price"]].merge(
    g[["listing_date", "issue_price_r", "listing_price_src"]], on=["listing_date", "issue_price_r"])
agree = ((mm["listing_price"] - mm["listing_price_src"]).abs() <= 0.5).mean()
print(f"\nMatched rows: {len(mm)} | tracker listing price within 0.5 of Kaggle's: {agree:.1%}")

# ---- 3) try to get past the 100-row cap for 2025 and 2026 ----
def page_text(resp):
    c = [v.decode("utf-8", "ignore") if isinstance(v, bytes) else v
         for v in resp.values() if isinstance(v, (str, bytes))]
    return max(c, key=len) if c else ""

def values(k):
    if k in ("page", "p"): return range(2, 9)
    if k in ("start", "offset"): return range(100, 800, 100)
    return [1] if k == "all" else [500]

client, known, extra = IPOHttpClient(rate_limit_delay=2.0), set(zip(g["listing_date"], g["issue_price_r"])), []
print("\nPagination probe:")
for year in (2026, 2025):
    for k in ["page", "p", "start", "offset", "limit", "per_page", "length", "all"]:
        got = 0
        for v in values(k):
            html = page_text(client.get(URL, params={"year": year, k: v}))
            if "reportTable" not in html:
                break
            df = parse_tracker_html(html, year)
            df["issue_price_r"] = df["issue_price"].round(2)
            new = df[[(d, p) not in known for d, p in zip(df["listing_date"], df["issue_price_r"])]]
            if new.empty:
                break
            known |= set(zip(new["listing_date"], new["issue_price_r"])); extra.append(new); got += len(new)
            (RAW / f"tracker_{year}_{k}{v}.html").write_text(html, encoding="utf-8")
        print(f"  {year} param '{k}': {got} new rows")
        if got:
            break

if extra:
    pd.concat(extra).to_csv(GM / "gmp_tracker_extra.csv", index=False)
    print("Saved extra rows:", sum(len(e) for e in extra))
else:
    print("\nNo pagination parameter worked. Hints from the saved 2026 page:")
    soup = BeautifulSoup((RAW / "tracker_2026.html").read_text(encoding="utf-8", errors="ignore"), "html.parser")
    for t in soup.find_all(string=re.compile(r"showing|entries|load more|show more|page \d", re.I)):
        print("  TEXT:", t.strip()[:120])
    for a in soup.select("[data-url], a[href*='page'], a[href*='start']")[:10]:
        print("  LINK:", str(a)[:160])