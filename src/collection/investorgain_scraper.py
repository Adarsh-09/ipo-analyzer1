"""
IPOVision — InvestorGain Scraper (Phase 1 Proof-of-Concept)
"""

import re
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.collection.http_client import IPOHttpClient

logger = logging.getLogger(__name__)


class InvestorGainScraper:
    """
    Scrapes IPO listing performance and subscription data from InvestorGain.
    """

    REPORT_URL = "https://www.investorgain.com/report/ipo-listing-day-performance/333/mainboard/"

    def __init__(self, client: Optional[IPOHttpClient] = None):
        self.client = client or IPOHttpClient(rate_limit_delay=2.0)

    @staticmethod
    def _clean_number(val: Optional[str]) -> Optional[float]:
        """Convert a string representation of a number to float, returning None if unparseable."""
        if not val:
            return None
        # Remove common word suffixes first
        cleaned = re.sub(r"(cr|crore|shares|per\s*share|times|x)", "", val, flags=re.I)
        # Remove currency symbols, commas, percentage signs, and whitespace
        cleaned = re.sub(r"[₹,%\s]", "", cleaned)
        # Handle '--' or empty indicators
        if cleaned in ["--", "-", "N/A", "NA", ""]:
            return None
        # Extract first valid numeric float
        match = re.search(r"[-+]?\d*\.?\d+", cleaned)
        if match:
            try:
                return float(match.group())
            except ValueError:
                return None
        return None

    @staticmethod
    def _clean_company_name(raw_name: str) -> Dict[str, Any]:
        """
        Extract clean company name and determine if it's Mainboard or SME.
        InvestorGain appends 'BSE SME', 'NSE SME', etc. to names.
        """
        is_sme = bool(re.search(r"\b(SME|BSE SME|NSE SME)\b", raw_name, re.I))
        # Remove SME markers and email protection artifacts
        clean = re.sub(r"(BSE SME|NSE SME|SME|\[email\s*protected\])", "", raw_name, flags=re.I)
        clean = re.sub(r"\s+", " ", clean).strip()
        return {"company_name": clean, "is_sme": is_sme}

    @staticmethod
    def _parse_subscription_multiple(val: Optional[str]) -> Optional[float]:
        """
        Parse subscription rate like '12.79x', '12.79 5th Nov', or '12.795th Nov'.
        Notice '5th' is an ordinal day attached to the 2-decimal subscription figure.
        """
        if not val:
            return None
        val_clean = val.strip()
        # Match standard float with up to 2 decimal places at the start
        match = re.match(r"^(\d+(?:\.\d{1,2})?)", val_clean)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        return None

    def fetch_listing_performance(self) -> List[Dict[str, Any]]:
        """Fetch and parse the IPO listing performance table."""
        logger.info(f"Fetching: {self.REPORT_URL}")
        resp = self.client.get(self.REPORT_URL)

        if not resp["success"]:
            logger.error(f"Failed to fetch: {resp['error']}")
            return []

        soup = BeautifulSoup(resp["text"], "lxml")
        table = soup.find("table", id="reportTable") or soup.find("table", class_="report-data-table")

        if not table:
            logger.warning("Could not find listing performance table on page.")
            return []

        thead = table.find("thead")
        headers = []
        if thead:
            for th in thead.find_all("th"):
                text = re.sub(r"[▲▼🔥]", "", th.get_text(strip=True)).strip()
                headers.append(text.lower())

        tbody = table.find("tbody")
        if not tbody:
            return []

        records = []
        for tr in tbody.find_all("tr"):
            cells = [td.get_text(strip=True) for td in tr.find_all("td")]
            if not cells or len(cells) < 5:
                continue

            row = {}
            for i, cell in enumerate(cells):
                key = headers[i] if i < len(headers) else f"col_{i}"
                row[key] = cell

            raw_name = row.get("name", "")
            name_info = self._clean_company_name(raw_name)

            if name_info["is_sme"]:
                continue

            record = {
                "source": "investorgain",
                "source_url": self.REPORT_URL,
                "scraped_at": datetime.now().isoformat(),
                "company_name": name_info["company_name"],
                "is_sme": False,
                "overall_subscription": self._parse_subscription_multiple(row.get("total")),
                "qib_subscription": self._clean_number(row.get("qib")),
                "nii_subscription": self._clean_number(row.get("nii")),
                "retail_subscription": self._clean_number(row.get("rii")),
                "issue_price": self._clean_number(row.get("ipo price")),
                "issue_size_cr": self._clean_number(row.get("ipo size")),
                "pe_ratio": self._clean_number(row.get("p/e")),
                "closing_date": row.get("closing date"),
            }
            records.append(record)

        logger.info(f"Successfully parsed {len(records)} mainboard IPO records.")
        return records
