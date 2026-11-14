from io import StringIO
from pathlib import Path
import pandas as pd
from bs4 import BeautifulSoup

pd.set_option("display.width", 220); pd.set_option("display.max_columns", None)
files = sorted(Path("data/raw/ipo_master/detail_pages").glob("*.html"))
print(len(files), "saved pages")

for f in files:
    soup = BeautifulSoup(f.read_text(encoding="utf-8", errors="ignore"), "html.parser")
    tables = [t for t in soup.find_all("table") if "gmp" in t.get_text(" ", strip=True).lower()]
    n_gmp_words = soup.get_text(" ").lower().count("gmp")
    print(f"\n{f.name}: {len(tables)} GMP table(s), word 'gmp' appears {n_gmp_words} times")
    for t in tables[:2]:
        try:
            print(pd.read_html(StringIO(str(t)))[0].head(12).to_string())
        except Exception as e:
            print("could not parse table:", e)