
import csv
from pathlib import Path

INPUT_FILE = Path(
    "data/interim/ipo_master/ipo_dates_2020.csv"
)

OUTPUT_FILE = Path(
    "data/interim/ipo_master/ipo_date_verification_2020.csv"
)

if not INPUT_FILE.exists():
    raise FileNotFoundError(INPUT_FILE)

if OUTPUT_FILE.exists():
    raise FileExistsError(
        f"{OUTPUT_FILE} already exists. "
        "Review it instead of overwriting it."
    )

with INPUT_FILE.open(
    "r", encoding="utf-8-sig", newline=""
) as file:
    records = list(csv.DictReader(file))

verification_records = []

for record in records:

    is_rossari = (
        record.get("company_name", "").strip().lower()
        == "rossari biotech"
    )

    if is_rossari:
        issue_open_official = "2020-07-13"
        issue_close_official = "2020-07-15"
        listing_official = "2020-07-23"

        issue_source = "Rossari Biotech RHP"
        issue_url = (
            "https://www.axiscapital.co.in/public/contents/"
            "Rossari-Biotech-Limited-RHP.pdf"
        )

        listing_source = "NSE-hosted company filing"
        listing_url = (
            "https://nsearchives.nseindia.com/corporate/"
            "ROSSARI_21082020165351_20200821_"
            "Outcome_of_Board_Meeting_.pdf"
        )

        corroborating_url = (
            "https://nsearchives.nseindia.com/web/sites/"
            "default/files/inline-files/Market_Pulse_Aug_2020.pdf"
        )

        status = "verified"

        notes = (
            "Issue dates confirmed from RHP. Listing date "
            "confirmed from NSE-hosted company filing and "
            "corroborated by NSE Market Pulse."
        )

    else:
        issue_open_official = ""
        issue_close_official = ""
        listing_official = ""

        issue_source = ""
        issue_url = ""
        listing_source = ""
        listing_url = ""
        corroborating_url = ""

        status = "pending"
        notes = "Awaiting independent official verification."

    verification_records.append({

        "company_name": record["company_name"],
        "symbol": record["symbol"],
        "bse_scrip_code": record["bse_scrip_code"],

        "issue_open_date_extracted": record["issue_open_date"],
        "issue_open_date_official": issue_open_official,

        "issue_close_date_extracted": record["issue_close_date"],
        "issue_close_date_official": issue_close_official,

        "listing_date_extracted": record["listing_date_detail"],
        "listing_date_reference": record["listing_date_reference"],
        "listing_date_official": listing_official,

        "detail_url": record["detail_url"],

        "issue_dates_source_name": issue_source,
        "issue_dates_source_url": issue_url,

        "listing_date_source_name": listing_source,
        "listing_date_source_url": listing_url,
        "listing_corroborating_source_url": corroborating_url,

        "verification_status": status,
        "verification_notes": notes
    })


OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

with OUTPUT_FILE.open(
    "w", encoding="utf-8-sig", newline=""
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=list(verification_records[0].keys())
    )

    writer.writeheader()
    writer.writerows(verification_records)

print("Verification ledger created successfully!")
print("Total records:", len(verification_records))

print(
    "Verified:",
    sum(r["verification_status"] == "verified"
        for r in verification_records)
)

print(
    "Pending:",
    sum(r["verification_status"] == "pending"
        for r in verification_records)
)

print("Output:", OUTPUT_FILE)
