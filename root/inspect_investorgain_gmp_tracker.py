
from pathlib import Path
from bs4 import BeautifulSoup

from src.collection.http_client import IPOHttpClient

URL = (
    "https://www.investorgain.com/report/"
    "ipo-gmp-performance-tracker/377/ipo/"
)

client = IPOHttpClient(rate_limit_delay=2.0)

print("Testing alternative historical IPO source...")

response = client.get(URL, params={"year": 2020})

if not response["success"]:
    print("Request failed:", response["error"])
    print("HTTP status:", response["status_code"])
    raise SystemExit(1)

html = response["text"]

print("\nHTTP status:", response["status_code"])
print("Content type:", response["content_type"])
print("HTML length:", len(html))

# Save a separate raw HTML snapshot.
raw_dir = Path("data/raw/ipo_master")
raw_dir.mkdir(parents=True, exist_ok=True)

html_path = raw_dir / "investorgain_gmp_tracker_2020.html"
html_path.write_text(html, encoding="utf-8")

print("\nSaved:", html_path)

soup = BeautifulSoup(html, "lxml")

if soup.title:
    print("\nPage title:", soup.title.get_text(strip=True))

table = soup.find("table", id="reportTable")

if table is None:
    print("\nreportTable not found.")
    print(soup.get_text(" ", strip=True)[:1500])
    raise SystemExit(1)

print("\nTable ID:", table.get("id"))
print("Table classes:", table.get("class"))

# Inspect the first rows without assuming the header structure.
rows = table.find_all("tr")

print("\nTotal HTML table rows:", len(rows))

for index, tr in enumerate(rows[:8], start=1):
    cells = [
        cell.get_text(" ", strip=True)
        for cell in tr.find_all(["th", "td"])
    ]

    print(f"\nRow {index}:")
    print(cells)

print("\nInspection completed.")
