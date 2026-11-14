
import csv
import json
import re
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from src.collection.http_client import IPOHttpClient


# --------------------------------------------------
# 1. Configuration
# --------------------------------------------------

YEAR = 2020

BASE_URL = (
    "https://www.investorgain.com/report/"
    "ipo-gmp-performance-tracker/377/ipo/"
)

SOURCE_URL = f"{BASE_URL}?year={YEAR}"

OUTPUT_DIR = Path("data/interim/ipo_master")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / f"ipo_master_candidates_{YEAR}.csv"


# --------------------------------------------------
# 2. Date cleaning function
# --------------------------------------------------

def clean_listing_date(raw_date):
    """
    Convert listing dates into YYYY-MM-DD format.
    Return None if the date cannot be parsed.
    """

    if not raw_date:
        return None

    formats = [
        "%d-%b-%y",
        "%d-%b-%Y",
        "%Y-%m-%d",
    ]

    for date_format in formats:
        try:
            parsed = datetime.strptime(
                raw_date.strip(),
                date_format
            )
            return parsed.strftime("%Y-%m-%d")

        except ValueError:
            continue

    return None


# --------------------------------------------------
# 3. Fetch historical page
# --------------------------------------------------

print(f"Collecting IPO candidates for {YEAR}...")

client = IPOHttpClient(rate_limit_delay=2.0)

response = client.get(
    BASE_URL,
    params={"year": YEAR}
)

if not response["success"]:
    raise RuntimeError(
        f"Request failed: {response['error']}"
    )

soup = BeautifulSoup(response["text"], "lxml")

table = soup.find("table", id="reportTable")

if table is None:
    raise RuntimeError("IPO history table not found.")


# --------------------------------------------------
# 4. Extract and normalize headers
# --------------------------------------------------

header_row = table.find("tr")

if header_row is None:
    raise RuntimeError("Header row not found.")

headers = []

for cell in header_row.find_all(["th", "td"]):

    header = cell.get_text(" ", strip=True)

    # Remove sorting arrows and decorative symbols.
    header = re.sub(r"[▲▼🔥]", "", header)

    headers.append(header.strip().lower())

print("\nDetected headers:")
print(headers)


# --------------------------------------------------
# 5. Validate required columns
# --------------------------------------------------

required_columns = ["ipo", "symbol", "listing dt"]

missing_columns = [
    col for col in required_columns
    if col not in headers
]

if missing_columns:
    raise ValueError(
        f"Missing required columns: {missing_columns}"
    )

# Map each header to its column index.
column_index = {
    header: index
    for index, header in enumerate(headers)
}


# --------------------------------------------------
# 6. Extract candidate records
# --------------------------------------------------

candidates = []

for row_number, tr in enumerate(
    table.find_all("tr")[1:],
    start=2
):

    cells = [
        td.get_text(" ", strip=True)
        for td in tr.find_all("td")
    ]

    # Ignore rows without actual data.
    if not cells or not any(cells):
        continue

    if len(cells) < len(headers):
        print(f"Skipping incomplete row {row_number}")
        continue

    raw_row = dict(zip(headers, cells))
    # Extract the individual IPO detail-page URL
    ipo_cell_index = column_index["ipo"]

    ipo_cell = tr.find_all("td")[ipo_cell_index]

    anchor = ipo_cell.find("a", href=True)

    detail_url = None

    if anchor:
        detail_url = urljoin(
            "https://www.investorgain.com",
            anchor["href"]
        )

    company_name = raw_row.get("ipo", "").strip()
    symbol = raw_row.get("symbol", "").strip()
    listing_date_raw = raw_row.get("listing dt", "").strip()

    if not company_name or not symbol:
        print(f"Skipping row {row_number}: missing identity")
        continue

    listing_date = clean_listing_date(listing_date_raw)

    candidate = {
        "company_name": company_name,
        "symbol": symbol,
        "listing_date": listing_date,
        "listing_date_raw": listing_date_raw,
        "detail_url": detail_url,
        "source": "investorgain",
        "source_url": SOURCE_URL,
        "source_year": YEAR,
        "review_status": "unreviewed",
        "raw_row_json": json.dumps(
            raw_row,
            ensure_ascii=False
        ),
    }

    candidates.append(candidate)


# --------------------------------------------------
# 7. Save candidate CSV
# --------------------------------------------------

if not candidates:
    raise RuntimeError("No IPO candidate records extracted.")

fieldnames = list(candidates[0].keys())

with OUTPUT_FILE.open(
    "w",
    newline="",
    encoding="utf-8-sig"
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=fieldnames
    )

    writer.writeheader()
    writer.writerows(candidates)


# --------------------------------------------------
# 8. Display extraction summary
# --------------------------------------------------

print("\nCollection completed!")

print("Year:", YEAR)
print("Candidate records:", len(candidates))
print("Output file:", OUTPUT_FILE)

print("\nExtracted candidates:")

for candidate in candidates:
    print(
        candidate["company_name"],
        "|",
        candidate["symbol"],
        "|",
        candidate["listing_date"]
    )

# Check duplicate symbol + listing date combinations.
seen = set()
duplicates = []

for candidate in candidates:

    key = (
        candidate["symbol"].upper(),
        candidate["listing_date"]
    )

    if key in seen:
        duplicates.append(key)

    seen.add(key)

print("\nDuplicate combinations:", duplicates)
print("\nNo canonical IPO IDs have been assigned.")
