import re
from io import StringIO
from pathlib import Path
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]

def _num(text):
    """'₹-14' -> -14.0, '₹10340.79 Cr' -> 10340.79, '79.37x' -> 79.37, '' -> NaN"""
    if text is None:
        return np.nan
    m = re.search(r"-?\d[\d,]*\.?\d*", str(text).replace("₹", "").replace("−", "-"))
    return float(m.group().replace(",", "")) if m else np.nan

def parse_tracker_html(html: str, source_year: int) -> pd.DataFrame:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one("table#reportTable")
    rows = []
    for tr in table.find_all("tr"):
        cells = {td.get("data-label"): td.get_text(" ", strip=True)
                 for td in tr.find_all("td") if td.get("data-label")}
        if not cells.get("IPO") or cells["IPO"] == "IPO":
            continue                                   # blank rows and repeated header rows
        symbol_text = cells.get("Symbol", "")
        parts = [p.strip() for p in symbol_text.split(",")]
        link = tr.select_one("a[href]")
        est_price = _num(cells.get("Est Price"))
        gmp_raw = _num(cells.get("GMP"))
        rows.append({
            "source_year": source_year,
            "company_name": cells["IPO"],
            "symbol": parts[0] if parts else None,
            "bse_code": parts[1] if len(parts) > 1 else None,
            "listing_date": pd.to_datetime(cells.get("Listing Dt"), format="%d-%b-%y", errors="coerce"),
            "issue_size_cr": _num(cells.get("Size")),
            "total_sub": _num(cells.get("Sub")),
            "issue_price": _num(cells.get("Price")),
            "gmp_rs": gmp_raw if not np.isnan(est_price) else np.nan,   # blank Est Price = GMP missing, never 0
            "est_price": est_price,
            "listing_price_src": _num(cells.get("Listing Price")),      # for sanity checks ONLY, never a feature
            "detail_path": link["href"] if link else None,
        })
    df = pd.DataFrame(rows).dropna(subset=["listing_date"])
    df["gmp_missing"] = df["gmp_rs"].isna().astype(int)
    df["gmp_pct_of_issue"] = df["gmp_rs"] / df["issue_price"] * 100
    return df

if __name__ == "__main__":
    pd.set_option("display.width", 220); pd.set_option("display.max_columns", None)
    path = ROOT / "data/raw/ipo_master/investorgain_gmp_tracker_2020.html"
    df = parse_tracker_html(path.read_text(encoding="utf-8", errors="ignore"), 2020)
    print(df.drop(columns=["detail_path", "listing_price_src"]).to_string())
    print("\nRows:", len(df), "| GMP missing:", int(df["gmp_missing"].sum()))
    out = ROOT / "data/interim/gmp"; out.mkdir(parents=True, exist_ok=True)
    df.to_csv(out / "gmp_tracker_2020_parsed.csv", index=False)