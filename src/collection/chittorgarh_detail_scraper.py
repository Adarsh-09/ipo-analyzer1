"""
IPOVision — Chittorgarh Detail Page Scraper (Phase 1 Proof-of-Concept)
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


class ChittorgarhDetailScraper:
    """Extracts structured fundamental, valuation, and issue data from Chittorgarh IPO pages."""

    def __init__(self, client: Optional[IPOHttpClient] = None):
        self.client = client or IPOHttpClient(rate_limit_delay=2.0)

    @staticmethod
    def _clean_number(val: Optional[str]) -> Optional[float]:
        """Convert string numbers like '₹53.41Cr', '₹111 per share', '1,200', '12.99%' to float."""
        if not val:
            return None
        # Remove common word suffixes first BEFORE stripping whitespace
        cleaned = re.sub(r"(cr|crore|shares|per\s*share|times)", "", val, flags=re.I)
        cleaned = re.sub(r"[₹,%\s]", "", cleaned)
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

    def parse_detail_page(self, url: str) -> Dict[str, Any]:
        """Parse a Chittorgarh IPO detail page into structured data."""
        logger.info(f"Parsing detail page: {url}")
        resp = self.client.get(url)

        if not resp["success"]:
            logger.error(f"Failed to fetch {url}: {resp['error']}")
            return {"error": resp["error"]}

        soup = BeautifulSoup(resp["text"], "lxml")
        tables = soup.find_all("table")

        result = {
            "source": "chittorgarh",
            "source_url": url,
            "scraped_at": datetime.now().isoformat(),
            "tables_found": len(tables),
            "issue_details": {},
            "issue_size": {},
            "financials_multi_year": [],
            "kpis": {},
            "valuation": {},
            "promoter_holding": {},
            "listing_details": {},
        }

        title_tag = soup.find("h1")
        if title_tag:
            result["company_name"] = re.sub(r"\s+IPO.*", "", title_tag.get_text(strip=True))

        for table in tables:
            rows = table.find_all("tr")
            if not rows:
                continue

            first_row_text = " ".join([c.get_text(strip=True) for c in rows[0].find_all(["th", "td"])])
            first_row_lower = first_row_text.lower()

            if "ipo date" in first_row_lower or "face value" in first_row_lower:
                for row in rows:
                    cells = [c.get_text(strip=True) for c in row.find_all(["th", "td"])]
                    if len(cells) >= 2:
                        key = cells[0].lower().replace(" ", "_")
                        result["issue_details"][key] = cells[1]

            elif "issue size" in first_row_lower or "fresh issue" in first_row_lower:
                for row in rows:
                    cells = [c.get_text(strip=True) for c in row.find_all(["th", "td"])]
                    if len(cells) >= 2:
                        key = cells[0].lower().replace(" ", "_")
                        result["issue_size"][key] = cells[1]

            elif "period ended" in first_row_lower:
                headers = [c.get_text(strip=True) for c in rows[0].find_all(["th", "td"])]
                for row in rows[1:]:
                    cells = [c.get_text(strip=True) for c in row.find_all(["th", "td"])]
                    if len(cells) == len(headers):
                        metric_name = cells[0]
                        row_data = {"metric": metric_name}
                        for col_idx, period in enumerate(headers[1:], start=1):
                            row_data[period] = self._clean_number(cells[col_idx])
                        result["financials_multi_year"].append(row_data)

            elif "kpi" in first_row_lower or "ronw" in first_row_lower:
                for row in rows[1:]:
                    cells = [c.get_text(strip=True) for c in row.find_all(["th", "td"])]
                    if len(cells) >= 2:
                        key = cells[0].lower().replace(" ", "_")
                        result["kpis"][key] = self._clean_number(cells[1])

            elif "valuation metric" in first_row_lower or "p/e (x)" in first_row_lower:
                for row in rows[1:]:
                    cells = [c.get_text(strip=True) for c in row.find_all(["th", "td"])]
                    if len(cells) >= 2:
                        metric = cells[0].lower().replace(" ", "_")
                        pre_val = self._clean_number(cells[1]) if len(cells) > 1 else None
                        post_val = self._clean_number(cells[2]) if len(cells) > 2 else None
                        result["valuation"][metric] = {"pre_ipo": pre_val, "post_ipo": post_val}

            elif "price details" in first_row_lower or "open" in first_row_lower:
                for row in rows:
                    cells = [c.get_text(strip=True) for c in row.find_all(["th", "td"])]
                    if len(cells) >= 2:
                        key = cells[0].lower().replace(" ", "_")
                        result["listing_details"][key] = self._clean_number(cells[1])

        return result
