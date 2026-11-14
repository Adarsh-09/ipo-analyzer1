
import re
import json

from pathlib import Path
from datetime import datetime

from bs4 import BeautifulSoup

from src.collection.http_client import IPOHttpClient


# --------------------------------------------------
# 1. Configuration
# --------------------------------------------------

COMPANY = "Rossari Biotech"

URL = (
    "https://www.investorgain.com/"
    "gmp/rossari-biotech-ipo/14/"
)

RAW_DIR = Path("data/raw/ipo_master")
OUTPUT_DIR = Path("data/interim/ipo_master")

RAW_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# 2. Date conversion
# --------------------------------------------------

def normalize_date(raw_date):
    """
    Convert dates such as:
        13th Jul 2020
        15th July 2020

    Into:
        2020-07-13
        2020-07-15
    """

    if not raw_date:
        return None

    # Remove ordinal suffixes: st, nd, rd, th
    clean_date = re.sub(
        r"(\d{1,2})(st|nd|rd|th)\b",
        r"\1",
        raw_date.strip(),
        flags=re.IGNORECASE
    )

    formats = [
        "%d %b %Y",
        "%d %B %Y"
    ]

    for fmt in formats:
        try:
            parsed = datetime.strptime(clean_date, fmt)
            return parsed.strftime("%Y-%m-%d")

        except ValueError:
            continue

    return None


# --------------------------------------------------
# 3. Fetch detail page
# --------------------------------------------------

print(f"Fetching details for {COMPANY}...")

client = IPOHttpClient(rate_limit_delay=2.0)

response = client.get(URL)

if not response["success"]:
    raise RuntimeError(
        f"Request failed: {response['error']}"
    )

html = response["text"]

print("HTTP Status:", response["status_code"])
print("HTML Size:", len(html))


# --------------------------------------------------
# 4. Save original HTML
# --------------------------------------------------

raw_file = RAW_DIR / "rossari_biotech_detail.html"

raw_file.write_text(
    html,
    encoding="utf-8"
)

print("Raw HTML saved:", raw_file)


# --------------------------------------------------
# 5. Extract page text
# --------------------------------------------------

soup = BeautifulSoup(html, "lxml")

page_title = (
    soup.title.get_text(" ", strip=True)
    if soup.title
    else None
)

# Collapse newlines and extra spaces.
page_text = re.sub(
    r"\s+",
    " ",
    soup.get_text(" ", strip=True)
)


# --------------------------------------------------
# 6. Find Opened, Closed and Listed dates
# --------------------------------------------------

date_pattern = re.compile(
    r"Opened\s*[-:]\s*"
    r"(?P<opened>\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+\s+\d{4})"
    r"\s+Closed\s*[-:]\s*"
    r"(?P<closed>\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+\s+\d{4})"
    r"\s+Listed\s*[-:]\s*"
    r"(?P<listed>\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+\s+\d{4})",
    flags=re.IGNORECASE
)

match = date_pattern.search(page_text)

if not match:

    print("\nCould not find the expected date pattern.")

    # Display context for debugging.
    position = page_text.lower().find("opened")

    if position >= 0:
        print(page_text[position:position + 250])
    else:
        print("The word 'Opened' was not found.")

    raise RuntimeError("IPO date extraction failed.")


# --------------------------------------------------
# 7. Normalize dates
# --------------------------------------------------

raw_open_date = match.group("opened")
raw_close_date = match.group("closed")
raw_listing_date = match.group("listed")

record = {
    "company_name": COMPANY,

    "issue_open_date": normalize_date(raw_open_date),

    "issue_close_date": normalize_date(raw_close_date),

    "listing_date": normalize_date(raw_listing_date),

    "source_name": "InvestorGain",

    "source_url": URL,

    "page_title": page_title,

    "retrieved_at": datetime.now().astimezone().isoformat(),

    "verification_status": "unverified"
}


# --------------------------------------------------
# 8. Validate date sequence
# --------------------------------------------------

if not all([
    record["issue_open_date"],
    record["issue_close_date"],
    record["listing_date"]
]):
    raise ValueError("One or more dates could not be normalized.")

if not (
    record["issue_open_date"]
    <= record["issue_close_date"]
    <= record["listing_date"]
):
    raise ValueError("IPO date sequence is invalid.")


# --------------------------------------------------
# 9. Save extracted record
# --------------------------------------------------

output_file = OUTPUT_DIR / "rossari_issue_dates_test.json"

with output_file.open("w", encoding="utf-8") as file:
    json.dump(record, file, indent=4, ensure_ascii=False)


# --------------------------------------------------
# 10. Display result
# --------------------------------------------------

print("\nExtraction successful!")

for key, value in record.items():
    print(f"{key}: {value}")

print("\nOutput saved:", output_file)
