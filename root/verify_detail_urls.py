
import csv
from pathlib import Path

FILE = Path(
    "data/interim/ipo_master/ipo_master_review_2020.csv"
)

if not FILE.exists():
    raise FileNotFoundError(FILE)

with FILE.open(
    "r",
    encoding="utf-8-sig",
    newline=""
) as f:
    reader = csv.DictReader(f)

    print("CSV columns:")
    print(reader.fieldnames)

    records = list(reader)

print("\nTotal records:", len(records))

if "detail_url" not in (reader.fieldnames or []):
    raise ValueError("detail_url column is missing!")

valid_urls = [
    r for r in records
    if r.get("detail_url", "").startswith("https://")
]

missing_urls = [
    r for r in records
    if not r.get("detail_url", "").strip()
]

print("Valid detail URLs:", len(valid_urls))
print("Missing detail URLs:", len(missing_urls))

print("\nCompany-wise detail URLs:")

for record in records:
    print(
        record["company_name"],
        "->",
        record["detail_url"]
    )

print("\nVerification completed.")
