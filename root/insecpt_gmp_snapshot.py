from io import StringIO
from pathlib import Path
import pandas as pd
from bs4 import BeautifulSoup

pd.set_option("display.width", 250); pd.set_option("display.max_columns", None)
pd.set_option("display.max_colwidth", 45)

html = Path("E:/ipo-analyzer1/data/raw/ipo_master/investorgain_gmp_tracker_2020.html").read_text(encoding="utf-8", errors="ignore")
soup = BeautifulSoup(html, "html.parser")
table = soup.select_one("table#reportTable")

df = pd.read_html(StringIO(str(table)))[0]
print("Shape:", df.shape)
print("Columns:", list(df.columns))
print(df.head(20).to_string())
print("\nMissing per column:\n", df.isna().sum())

rows = table.select("tbody tr") or table.select("tr")
print("\n--- Raw HTML of the first data row ---")
print(str(rows[1] if len(rows) > 1 else rows[0])[:1500])

links = [a["href"] for a in table.select("a[href]")]
print("\nLinks in table:", len(links)); print(links[:5])

# Any note about when the GMP values were taken
for t in soup.find_all(string=lambda s: s and ("gmp" in s.lower()) and len(s.strip()) < 200):
    print("TEXT:", t.strip()[:160])