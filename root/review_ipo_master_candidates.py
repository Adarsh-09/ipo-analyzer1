
import csv
import re
from pathlib import Path


# --------------------------------------------------
# 1. File locations
# --------------------------------------------------

INPUT_FILE = Path(
    "data/interim/ipo_master/ipo_master_candidates_2020.csv"
)

OUTPUT_FILE = Path(
    "data/interim/ipo_master/ipo_master_review_2020.csv"
)


# --------------------------------------------------
# 2. Known instrument classifications
# --------------------------------------------------

KNOWN_CLASSIFICATIONS = {
    "yes bank": {
        "instrument_type": "FPO",
        "scope_decision": "exclude",
        "type_status": "verified",
        "type_source": "Chittorgarh FPO Note",
        "type_source_url": (
            "https://www.chittorgarh.net/reports/ipo_notes/"
            "angelbroking_iponote_yesbank.pdf"
        ),
        "reason": "Follow-on public offer, not an IPO."
    },

    "mindspace reit": {
        "instrument_type": "REIT",
        "scope_decision": "exclude",
        "type_status": "verified",
        "type_source": "SEBI REIT filing",
        "type_source_url": (
            "https://www.sebi.gov.in/filings/reit-issues/"
            "aug-2020/mindspace-business-parks-reit_47263.html"
        ),
        "reason": "REIT public issue, not an ordinary company IPO."
    }
}


# --------------------------------------------------
# 3. Verified listing date correction
# --------------------------------------------------

VERIFIED_DATES = {
    "route mobile": {
        "listing_date": "2020-09-21",
        "source_name": "Route Mobile Annual Report 2020-21",
        "source_url": (
            "https://www.routemobile.com/wp-content/uploads/"
            "2021/11/Annual-Report-2021.pdf"
        )
    }
}


# --------------------------------------------------
# 4. Symbol cleaning function
# --------------------------------------------------

def split_symbol(raw_symbol):
    """
    Split combined InvestorGain symbol into:
    NSE trading symbol and BSE scrip code.

    Example:
        SBICARD, 543066
        -> SBICARD, 543066
    """

    if not raw_symbol:
        return None, None

    match = re.fullmatch(
        r"\s*([A-Za-z0-9.&-]+)\s*,\s*(\d+)\s*",
        raw_symbol
    )

    if match:
        symbol = match.group(1).upper()
        bse_code = match.group(2)

        return symbol, bse_code

    # Preserve an unexpected value for manual investigation.
    return raw_symbol.strip().upper(), None


# --------------------------------------------------
# 5. Read extracted candidates
# --------------------------------------------------

if not INPUT_FILE.exists():
    raise FileNotFoundError(INPUT_FILE)

with INPUT_FILE.open(
    "r",
    newline="",
    encoding="utf-8-sig"
) as file:

    reader = csv.DictReader(file)
    candidates = list(reader)


# --------------------------------------------------
# 6. Review every candidate
# --------------------------------------------------

review_records = []

for candidate in candidates:

    company_name = candidate["company_name"].strip()

    name_key = company_name.lower()

    raw_symbol = candidate.get("symbol", "")

    clean_symbol, bse_code = split_symbol(raw_symbol)

    listing_date_scraped = candidate.get(
        "listing_date", ""
    )

    classification = KNOWN_CLASSIFICATIONS.get(
        name_key,
        {
            "instrument_type": "IPO_CANDIDATE",
            "scope_decision": "pending",
            "type_status": "pending",
            "type_source": "",
            "type_source_url": "",
            "reason": "Requires secondary verification."
        }
    )

    date_info = VERIFIED_DATES.get(
        name_key,
        {
            "listing_date": "",
            "source_name": "",
            "source_url": ""
        }
    )

    review_records.append({

        "company_name": company_name,

        "source_symbol_raw": raw_symbol,

        "symbol": clean_symbol,

        "bse_scrip_code": bse_code,

        "detail_url": candidate.get("detail_url", ""),

        "listing_date_scraped": listing_date_scraped,

        "listing_date_verified": date_info["listing_date"],

        "instrument_type": classification["instrument_type"],

        "scope_decision": classification["scope_decision"],

        "type_verification_status": classification["type_status"],

        "type_source_name": classification["type_source"],

        "type_source_url": classification["type_source_url"],

        "listing_date_source_name": date_info["source_name"],

        "listing_date_source_url": date_info["source_url"],

        "review_status": (
            "partially_reviewed"
            if classification["scope_decision"] == "exclude"
            or date_info["listing_date"]
            else "pending"
        ),

        "verification_note": classification["reason"],

        "source_url": candidate["source_url"],

        "raw_row_json": candidate["raw_row_json"]
    })


# --------------------------------------------------
# 7. Save review dataset
# --------------------------------------------------

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

fieldnames = list(review_records[0].keys())

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
    writer.writerows(review_records)


# --------------------------------------------------
# 8. Print summary
# --------------------------------------------------

print("\nP3.1.3 Review Completed")

print("Total candidates:", len(review_records))

excluded = [
    r for r in review_records
    if r["scope_decision"] == "exclude"
]

pending = [
    r for r in review_records
    if r["scope_decision"] == "pending"
]

print("Excluded instruments:", len(excluded))
print("Pending IPO candidates:", len(pending))

print("\nExcluded records:")

for record in excluded:
    print(
        record["company_name"],
        "|",
        record["instrument_type"],
        "|",
        record["verification_note"]
    )

print("\nCleaned symbols:")

for record in review_records:
    print(
        record["company_name"],
        "|",
        record["symbol"],
        "| BSE:",
        record["bse_scrip_code"]
    )

print("\nOutput:", OUTPUT_FILE)
