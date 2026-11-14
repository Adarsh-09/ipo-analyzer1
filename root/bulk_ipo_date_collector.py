
import csv
import re
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup

from src.collection.http_client import IPOHttpClient


# ==================================================
# 1. CONFIGURATION
# ==================================================

INPUT_FILE = Path(
    "data/interim/ipo_master/ipo_master_review_2020.csv"
)

OUTPUT_FILE = Path(
    "data/interim/ipo_master/ipo_dates_2020.csv"
)

RAW_DIR = Path(
    "data/raw/ipo_master/detail_pages"
)

RAW_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)


# ==================================================
# 2. DATE EXTRACTION HELPERS
# ==================================================

DATE_TOKEN = (
    r"\d{1,2}(?:st|nd|rd|th)?\s+"
    r"[A-Za-z]{3,9},?\s+\d{4}"
)


def normalize_date(raw_date):
    """Convert a textual date into YYYY-MM-DD."""

    if not raw_date:
        return None

    cleaned = re.sub(
        r"(\d{1,2})(st|nd|rd|th)\b",
        r"\1",
        raw_date.strip(),
        flags=re.IGNORECASE
    )

    cleaned = cleaned.replace(",", "")

    formats = [
        "%d %b %Y",
        "%d %B %Y"
    ]

    for fmt in formats:
        try:
            parsed = datetime.strptime(cleaned, fmt)
            return parsed.strftime("%Y-%m-%d")

        except ValueError:
            continue

    return None


def extract_labelled_date(page_text, labels):
    """
    Find a date following a label such as:
    Opened - 13th Jul 2020
    Closed - 15th Jul 2020
    Listed - 23rd Jul 2020
    """

    for label in labels:

        pattern = (
            rf"\b{label}\b\s*[-:–]?\s*"
            rf"({DATE_TOKEN})"
        )

        match = re.search(
            pattern,
            page_text,
            flags=re.IGNORECASE
        )

        if match:
            return normalize_date(match.group(1))

    return None


def create_result(candidate):
    """Create a consistent result structure for every candidate."""

    return {
        "company_name": candidate.get("company_name", ""),
        "symbol": candidate.get("symbol", ""),
        "bse_scrip_code": candidate.get("bse_scrip_code", ""),
        "instrument_type": candidate.get("instrument_type", ""),

        "issue_open_date": "",
        "issue_close_date": "",
        "listing_date_detail": "",

        "listing_date_reference": (
            candidate.get("listing_date_verified", "")
            or candidate.get("listing_date_scraped", "")
        ),

        "listing_date_match": "not_checked",
        "date_sequence_valid": "",

        "detail_url": candidate.get("detail_url", ""),
        "source_name": "InvestorGain",

        "retrieved_at": datetime.now().astimezone().isoformat(),

        "raw_html_path": "",
        "extraction_status": "pending",
        "verification_status": "unverified",
        "error": ""
    }


# ==================================================
# 3. LOAD CANDIDATES
# ==================================================

if not INPUT_FILE.exists():
    raise FileNotFoundError(INPUT_FILE)

with INPUT_FILE.open(
    "r",
    encoding="utf-8-sig",
    newline=""
) as file:

    reader = csv.DictReader(file)
    candidates = list(reader)

print("Total candidate records:", len(candidates))


# Only process records whose scope decision is pending.
# FPOs and REITs remain excluded.

eligible_candidates = [
    candidate
    for candidate in candidates
    if candidate.get("scope_decision") == "pending"
]

print("Candidates selected:", len(eligible_candidates))
print("Excluded records skipped:", len(candidates) - len(eligible_candidates))


# ==================================================
# 4. INITIALIZE HTTP CLIENT
# ==================================================

client = IPOHttpClient(rate_limit_delay=2.0)

results = []


# ==================================================
# 5. PROCESS EACH IPO
# ==================================================

for index, candidate in enumerate(
    eligible_candidates,
    start=1
):

    result = create_result(candidate)

    company = candidate.get("company_name", "")
    url = candidate.get("detail_url", "")

    print(f"\n[{index}/{len(eligible_candidates)}] {company}")

    if not url.startswith("https://"):
        result["extraction_status"] = "failed"
        result["error"] = "Missing or invalid detail URL"
        results.append(result)
        print("Invalid URL. Skipping.")
        continue

    try:

        # Fetch page
        response = client.get(url)

        if not response["success"]:

            result["extraction_status"] = "failed"
            result["error"] = response["error"] or "HTTP request failed"

            print("Request failed:", result["error"])

            results.append(result)
            continue

        html = response["text"]

        # Save original HTML snapshot
        symbol = candidate.get("symbol", "unknown")

        raw_file = RAW_DIR / f"{symbol.lower()}_2020.html"

        raw_file.write_text(
            html,
            encoding="utf-8"
        )

        result["raw_html_path"] = str(raw_file)

        # Parse the HTML
        soup = BeautifulSoup(html, "lxml")

        page_text = re.sub(
            r"\s+",
            " ",
            soup.get_text(" ", strip=True)
        )

        # Extract all three dates
        open_date = extract_labelled_date(
            page_text,
            ["Opened", "Open Date", "Issue Open Date"]
        )

        close_date = extract_labelled_date(
            page_text,
            ["Closed", "Close Date", "Issue Close Date"]
        )

        listing_date = extract_labelled_date(
            page_text,
            ["Listed", "Listing Date"]
        )

        result["issue_open_date"] = open_date or ""
        result["issue_close_date"] = close_date or ""
        result["listing_date_detail"] = listing_date or ""

        # Check listing date against historical source
        reference_date = result["listing_date_reference"]

        if listing_date and reference_date:

            if listing_date == reference_date:
                result["listing_date_match"] = "match"

            else:
                result["listing_date_match"] = "mismatch"

        elif not listing_date:
            result["listing_date_match"] = "detail_date_missing"

        else:
            result["listing_date_match"] = "reference_missing"

        # Validate chronology
        if open_date and close_date and listing_date:

            valid_sequence = (
                open_date <= close_date <= listing_date
            )

            result["date_sequence_valid"] = valid_sequence

            if not valid_sequence:

                result["extraction_status"] = "invalid_date_sequence"

            elif result["listing_date_match"] == "mismatch":

                result["extraction_status"] = "needs_review"

            else:

                result["extraction_status"] = "extracted"

        else:

            result["extraction_status"] = "partial"

            missing = []

            if not open_date:
                missing.append("issue_open_date")

            if not close_date:
                missing.append("issue_close_date")

            if not listing_date:
                missing.append("listing_date")

            result["error"] = (
                "Missing fields: " + ", ".join(missing)
            )

        print("Opening:", open_date)
        print("Closing:", close_date)
        print("Listing:", listing_date)
        print("Status:", result["extraction_status"])

    except Exception as exc:

        result["extraction_status"] = "failed"
        result["error"] = str(exc)

        print("Error:", exc)

    results.append(result)


# ==================================================
# 6. SAVE RESULTS
# ==================================================

fieldnames = list(results[0].keys()) if results else []

if results:

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(results)

# Close the underlying HTTP session.
client.session.close()


# ==================================================
# 7. COLLECTION SUMMARY
# ==================================================

successful = [
    r for r in results
    if r["extraction_status"] == "extracted"
]

partial = [
    r for r in results
    if r["extraction_status"] == "partial"
]

failed = [
    r for r in results
    if r["extraction_status"] == "failed"
]

needs_review = [
    r for r in results
    if r["extraction_status"] in [
        "needs_review",
        "invalid_date_sequence"
    ]
]

print("\n" + "=" * 50)
print("IPO DATE COLLECTION SUMMARY")
print("=" * 50)

print("Total processed:", len(results))
print("Successfully extracted:", len(successful))
print("Partial records:", len(partial))
print("Failed records:", len(failed))
print("Records requiring review:", len(needs_review))

print("\nOutput:", OUTPUT_FILE)
print("Raw HTML directory:", RAW_DIR)

print("\nCollection finished.")
