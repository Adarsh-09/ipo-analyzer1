
from pathlib import Path
from bs4 import BeautifulSoup
from src.collection.http_client import IPOHttpClient

# 2020 mainboard IPO history page
URL = (
    "https://www.investorgain.com/report/"
    "ipo-performance-history/486/ipo/"
)

# Reuse our Phase 1 HTTP client
client = IPOHttpClient(rate_limit_delay=2.0)

print("Fetching InvestorGain historical IPO data...")

response = client.get(URL, params={"year": 2020})

# Step 1: Check HTTP response
if not response["success"]:
    print("Request failed!")
    print("Status:", response["status_code"])
    print("Error:", response["error"])
    raise SystemExit(1)

html = response["text"]

if not html:
    print("Empty HTML response!")
    raise SystemExit(1)

print("\nHTTP status:", response["status_code"])
print("Content type:", response["content_type"])
print("HTML size:", len(html), "characters")

# Step 2: Save the original HTML snapshot
raw_dir = Path("data/raw/ipo_master")
raw_dir.mkdir(parents=True, exist_ok=True)

html_path = raw_dir / "investorgain_mainboard_2020.html"
html_path.write_text(html, encoding="utf-8")

print("\nRaw HTML saved:", html_path)

# Step 3: Parse HTML
soup = BeautifulSoup(html, "lxml")

print("\nPage title:", soup.title.get_text(strip=True) if soup.title else "Not found")

# Step 4: Inspect available tables
tables = soup.find_all("table")

print("\nNumber of tables found:", len(tables))

for i, table in enumerate(tables):
    headers = [
        th.get_text(" ", strip=True)
        for th in table.select("thead th")
    ]

    print(f"\nTable {i + 1}")
    print("ID:", table.get("id"))
    print("Class:", table.get("class"))
    print("Headers:", headers)

# Step 5: Locate our IPO history table
table = soup.find("table", id="reportTable")

if table is None:
    for candidate in tables:
        headers = {
            th.get_text(" ", strip=True).lower()
            for th in candidate.select("thead th")
        }

        if any("ipo" == h.strip() for h in headers) and any(
            "symbol" in h for h in headers
        ):
            table = candidate
            break

if table is None:
    print("\nIPO history table not found.")
    raise SystemExit(1)

# Step 6: Extract rows for inspection only
tbody = table.find("tbody")

if tbody is None:
    print("Table body not found.")
    raise SystemExit(1)

rows = [
    tr for tr in tbody.find_all("tr")
    if tr.find_all("td")
]

print("\nNumber of data rows:", len(rows))

print("\nFirst five records:")

for row in rows[:5]:
    cells = [
        td.get_text(" ", strip=True)
        for td in row.find_all("td")
    ]
    print(cells)

print("\nInspection completed.")
