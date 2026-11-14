
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin

HTML_FILE = Path(
    "data/raw/ipo_master/investorgain_gmp_tracker_2020.html"
)

BASE_URL = "https://www.investorgain.com"

if not HTML_FILE.exists():
    raise FileNotFoundError(HTML_FILE)

html = HTML_FILE.read_text(encoding="utf-8")

soup = BeautifulSoup(html, "lxml")

table = soup.find("table", id="reportTable")

if table is None:
    raise RuntimeError("reportTable not found")

print("Inspecting IPO hyperlinks...\n")

for row in table.find_all("tr")[1:]:

    cells = row.find_all("td")

    if not cells:
        continue

    # First cell generally contains the IPO name.
    company_name = cells[0].get_text(" ", strip=True)

    if not company_name:
        continue

    links = []

    for anchor in row.find_all("a", href=True):

        full_url = urljoin(
            BASE_URL,
            anchor["href"]
        )

        links.append({
            "text": anchor.get_text(" ", strip=True),
            "url": full_url
        })

    print("IPO:", company_name)

    if links:
        for link in links:
            print("  Link text:", link["text"])
            print("  URL:", link["url"])
    else:
        print("  No hyperlink found")

    print("-" * 60)
