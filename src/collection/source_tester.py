"""
IPOVision — Data Source Tester (Phase 1)

Purpose:
    Systematically tests public data sources to determine whether the information
    required for IPOVision can be reliably collected. This is NOT a production
    scraper — it is a diagnostic tool that probes each source, inspects HTML
    structure, and records what works and what doesn't.

Data Flow:
    Source URL  -->  HTTP GET  -->  Check status code
                                     |
                                     v
                              Parse HTML with BeautifulSoup
                                     |
                                     v
                              Inspect structure (tables, selectors)
                                     |
                                     v
                              Record findings in a structured report

Usage:
    cd e:\\ipo-analyzer1
    .\.venv\Scripts\Activate.ps1
    python -m src.collection.source_tester
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.collection.http_client import IPOHttpClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


class SourceTestResult:
    """Stores the result of testing a single data source endpoint."""

    def __init__(self, source_name: str, url: str, category: str):
        self.source_name = source_name
        self.url = url
        self.category = category
        self.timestamp = datetime.now().isoformat()
        self.http_status: Optional[int] = None
        self.success: bool = False
        self.response_time_ms: Optional[float] = None
        self.content_type: Optional[str] = None
        self.page_size_kb: Optional[float] = None
        self.tables_found: int = 0
        self.relevant_selectors: List[str] = []
        self.sample_data: List[Dict[str, str]] = []
        self.data_fields_found: List[str] = []
        self.limitations: List[str] = []
        self.notes: str = ""
        self.error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_name": self.source_name,
            "url": self.url,
            "category": self.category,
            "timestamp": self.timestamp,
            "http_status": self.http_status,
            "success": self.success,
            "response_time_ms": self.response_time_ms,
            "content_type": self.content_type,
            "page_size_kb": self.page_size_kb,
            "tables_found": self.tables_found,
            "relevant_selectors": self.relevant_selectors,
            "sample_data": self.sample_data,
            "data_fields_found": self.data_fields_found,
            "limitations": self.limitations,
            "notes": self.notes,
            "error": self.error,
        }


class IPOSourceTester:
    """
    Tests accessibility and structure of public Indian IPO data sources.

    This class is the heart of Phase 1. It sends controlled HTTP requests to
    each candidate data source, parses the HTML response, and records:
    - Whether the page is accessible (HTTP 200).
    - What HTML tables or data structures exist.
    - Which IPO data fields can be extracted.
    - Any technical limitations (JavaScript rendering, CAPTCHAs, etc.).
    """

    def __init__(self):
        self.client = IPOHttpClient(rate_limit_delay=3.0)
        self.results: List[SourceTestResult] = []

    def _parse_html(self, html: str) -> BeautifulSoup:
        """Parse HTML content with lxml for speed, falling back to html.parser."""
        try:
            return BeautifulSoup(html, "lxml")
        except Exception:
            return BeautifulSoup(html, "html.parser")

    def _extract_table_headers(self, soup: BeautifulSoup) -> List[List[str]]:
        """Extract header rows from all HTML tables on the page."""
        table_headers = []
        for table in soup.find_all("table"):
            headers = []
            header_row = table.find("thead")
            if header_row:
                for th in header_row.find_all(["th", "td"]):
                    text = th.get_text(strip=True)
                    if text:
                        headers.append(text)
            if not headers:
                # Try first row of tbody or table directly
                first_row = table.find("tr")
                if first_row:
                    for cell in first_row.find_all(["th", "td"]):
                        text = cell.get_text(strip=True)
                        if text:
                            headers.append(text)
            if headers:
                table_headers.append(headers)
        return table_headers

    def _extract_sample_rows(
        self, soup: BeautifulSoup, max_tables: int = 3, max_rows: int = 3
    ) -> List[List[Dict[str, str]]]:
        """Extract a few sample data rows from HTML tables for inspection."""
        all_samples = []
        tables = soup.find_all("table")[:max_tables]

        for table in tables:
            # Get headers
            headers = []
            header_row = table.find("thead")
            if header_row:
                for th in header_row.find_all(["th", "td"]):
                    headers.append(th.get_text(strip=True))

            # Get data rows
            rows = []
            tbody = table.find("tbody") or table
            data_rows = tbody.find_all("tr")

            # Skip header row if no thead
            start = 0 if header_row else 1
            if not headers and data_rows:
                first_row = data_rows[0]
                headers = [c.get_text(strip=True) for c in first_row.find_all(["th", "td"])]
                start = 1

            for tr in data_rows[start : start + max_rows]:
                cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                if cells and headers:
                    row_dict = {}
                    for i, cell in enumerate(cells):
                        key = headers[i] if i < len(headers) else f"col_{i}"
                        row_dict[key] = cell
                    rows.append(row_dict)
                elif cells:
                    rows.append({f"col_{i}": c for i, c in enumerate(cells)})

            if rows:
                all_samples.append(rows)
        return all_samples

    # ──────────────────────────────────────────────────────────────────────
    # Individual Source Tests
    # ──────────────────────────────────────────────────────────────────────

    def test_chittorgarh_ipo_listing(self) -> SourceTestResult:
        """
        Test Chittorgarh IPO listing performance page.
        This is one of the most comprehensive public sources for Indian IPO data.
        It provides a historical table of mainboard IPO listing results.
        """
        url = "https://www.chittorgarh.com/report/ipo-listing-day-performance/82/"
        result = SourceTestResult("Chittorgarh IPO Listing Performance", url, "ipo_listing")
        logger.info(f"Testing: {result.source_name}")

        resp = self.client.get(url)
        result.http_status = resp["status_code"]
        result.response_time_ms = resp["elapsed_ms"]
        result.content_type = resp["content_type"]

        if not resp["success"]:
            result.error = resp["error"]
            result.limitations.append(f"Page not accessible: {resp['error']}")
            self.results.append(result)
            return result

        result.success = True
        html = resp["text"]
        result.page_size_kb = len(html) / 1024

        soup = self._parse_html(html)
        tables = soup.find_all("table")
        result.tables_found = len(tables)

        # Extract table headers to understand structure
        table_headers = self._extract_table_headers(soup)
        for i, headers in enumerate(table_headers):
            result.relevant_selectors.append(f"table[{i}]: {headers[:10]}")

        # Extract sample rows
        samples = self._extract_sample_rows(soup)
        if samples:
            result.sample_data = samples[0][:3]  # First table, first 3 rows

        # Check what IPO data fields are present
        page_text_lower = html.lower()
        field_checks = {
            "company_name": any(w in page_text_lower for w in ["company", "ipo name", "issue name"]),
            "issue_price": "issue price" in page_text_lower,
            "listing_price": any(w in page_text_lower for w in ["listing price", "listing open", "open price"]),
            "listing_gain": any(w in page_text_lower for w in ["listing gain", "listing day", "gain", "profit"]),
            "listing_date": any(w in page_text_lower for w in ["listing date", "list date"]),
            "issue_size": any(w in page_text_lower for w in ["issue size", "ipo size"]),
            "subscription": "subscription" in page_text_lower or "subscript" in page_text_lower,
        }
        result.data_fields_found = [k for k, v in field_checks.items() if v]

        result.notes = f"Found {len(tables)} tables. Page size: {result.page_size_kb:.0f} KB."
        self.results.append(result)
        return result

    def test_chittorgarh_ipo_detail(self) -> SourceTestResult:
        """
        Test Chittorgarh individual IPO detail page.
        These pages contain subscription data, financial info, and GMP for specific IPOs.
        """
        # Use a known recent IPO detail page as test
        url = "https://www.chittorgarh.com/ipo/swiggy-ipo/1670/"
        result = SourceTestResult("Chittorgarh IPO Detail Page", url, "ipo_detail")
        logger.info(f"Testing: {result.source_name}")

        resp = self.client.get(url)
        result.http_status = resp["status_code"]
        result.response_time_ms = resp["elapsed_ms"]
        result.content_type = resp["content_type"]

        if not resp["success"]:
            result.error = resp["error"]
            result.limitations.append(f"Detail page not accessible: {resp['error']}")
            self.results.append(result)
            return result

        result.success = True
        html = resp["text"]
        result.page_size_kb = len(html) / 1024

        soup = self._parse_html(html)
        tables = soup.find_all("table")
        result.tables_found = len(tables)

        table_headers = self._extract_table_headers(soup)
        for i, headers in enumerate(table_headers[:5]):
            result.relevant_selectors.append(f"table[{i}]: {headers[:8]}")

        # Check for specific detail fields
        page_text = html.lower()
        detail_fields = {
            "issue_price": "issue price" in page_text or "price band" in page_text,
            "issue_size": "issue size" in page_text,
            "fresh_issue": "fresh issue" in page_text,
            "ofs": "offer for sale" in page_text or "ofs" in page_text,
            "listing_date": "listing date" in page_text,
            "subscription_qib": "qib" in page_text,
            "subscription_nii": "nii" in page_text or "hni" in page_text,
            "subscription_retail": "retail" in page_text,
            "gmp": "grey market" in page_text or "gmp" in page_text,
            "pe_ratio": "p/e" in page_text or "pe ratio" in page_text,
            "eps": "eps" in page_text,
            "roe": "roe" in page_text or "ronw" in page_text,
            "promoter_holding": "promoter" in page_text,
            "lot_size": "lot size" in page_text,
            "listing_price": "listing" in page_text and "price" in page_text,
        }
        result.data_fields_found = [k for k, v in detail_fields.items() if v]

        samples = self._extract_sample_rows(soup, max_tables=3, max_rows=2)
        if samples:
            result.sample_data = samples[0][:2]

        result.notes = (
            f"Found {len(tables)} tables with detail data. "
            f"Fields detected: {len(result.data_fields_found)}. "
            f"Page size: {result.page_size_kb:.0f} KB."
        )
        self.results.append(result)
        return result

    def test_chittorgarh_gmp(self) -> SourceTestResult:
        """
        Test Chittorgarh GMP (Grey Market Premium) page.
        GMP is an unofficial sentiment indicator — not exchange-confirmed data.
        """
        url = "https://www.chittorgarh.com/report/ipo-grey-market-premium-latest-mainboard-ipo-gmp/82/"
        result = SourceTestResult("Chittorgarh GMP Page", url, "gmp")
        logger.info(f"Testing: {result.source_name}")

        resp = self.client.get(url)
        result.http_status = resp["status_code"]
        result.response_time_ms = resp["elapsed_ms"]
        result.content_type = resp["content_type"]

        if not resp["success"]:
            result.error = resp["error"]
            result.limitations.append(f"GMP page not accessible: {resp['error']}")
            self.results.append(result)
            return result

        result.success = True
        html = resp["text"]
        result.page_size_kb = len(html) / 1024

        soup = self._parse_html(html)
        tables = soup.find_all("table")
        result.tables_found = len(tables)

        table_headers = self._extract_table_headers(soup)
        for i, headers in enumerate(table_headers[:3]):
            result.relevant_selectors.append(f"table[{i}]: {headers[:8]}")

        samples = self._extract_sample_rows(soup, max_tables=2, max_rows=3)
        if samples:
            result.sample_data = samples[0][:3]

        page_text = html.lower()
        gmp_fields = {
            "gmp_value": "gmp" in page_text or "grey market" in page_text,
            "estimated_listing": "estimated" in page_text and "listing" in page_text,
            "ipo_name": "ipo" in page_text and ("name" in page_text or "company" in page_text),
            "issue_price": "price" in page_text,
            "updated_date": "updated" in page_text or "date" in page_text,
        }
        result.data_fields_found = [k for k, v in gmp_fields.items() if v]

        result.limitations.append("GMP is unofficial market sentiment — not exchange-confirmed.")
        result.limitations.append("Historical GMP time series may not be directly available on summary pages.")
        result.notes = f"Found {len(tables)} tables. Page size: {result.page_size_kb:.0f} KB."

        self.results.append(result)
        return result

    def test_investorgain_ipo_listing(self) -> SourceTestResult:
        """
        Test InvestorGain IPO listing performance page.
        Another comprehensive source for historical mainboard IPO data.
        """
        url = "https://www.investorgain.com/report/live-ipo-gmp/331/"
        result = SourceTestResult("InvestorGain IPO GMP", url, "gmp")
        logger.info(f"Testing: {result.source_name}")

        resp = self.client.get(url)
        result.http_status = resp["status_code"]
        result.response_time_ms = resp["elapsed_ms"]
        result.content_type = resp["content_type"]

        if not resp["success"]:
            result.error = resp["error"]
            result.limitations.append(f"Page not accessible: {resp['error']}")
            self.results.append(result)
            return result

        result.success = True
        html = resp["text"]
        result.page_size_kb = len(html) / 1024

        soup = self._parse_html(html)
        tables = soup.find_all("table")
        result.tables_found = len(tables)

        table_headers = self._extract_table_headers(soup)
        for i, headers in enumerate(table_headers[:3]):
            result.relevant_selectors.append(f"table[{i}]: {headers[:10]}")

        samples = self._extract_sample_rows(soup, max_tables=2, max_rows=3)
        if samples:
            result.sample_data = samples[0][:3]

        result.notes = f"Found {len(tables)} tables. Page size: {result.page_size_kb:.0f} KB."
        self.results.append(result)
        return result

    def test_nse_past_issues(self) -> SourceTestResult:
        """
        Test NSE India past IPO issues page.
        NSE is an authoritative source for listing prices and issue details,
        but often requires JavaScript rendering or has API-based data loading.
        """
        url = "https://www.nseindia.com/market-data/all-upcoming-issues-ipo"
        result = SourceTestResult("NSE India IPO Page", url, "ipo_listing")
        logger.info(f"Testing: {result.source_name}")

        resp = self.client.get(url)
        result.http_status = resp["status_code"]
        result.response_time_ms = resp["elapsed_ms"]
        result.content_type = resp["content_type"]

        if not resp["success"]:
            result.error = resp["error"]
            result.limitations.append(f"NSE page returned: {resp['error']}")
            result.limitations.append(
                "NSE India typically requires JavaScript rendering and "
                "may block automated requests. Data may need to be accessed "
                "through their internal API endpoints or alternative sources."
            )
            self.results.append(result)
            return result

        result.success = True
        html = resp["text"]
        result.page_size_kb = len(html) / 1024

        soup = self._parse_html(html)
        tables = soup.find_all("table")
        result.tables_found = len(tables)

        # NSE often loads data via JavaScript/API — check if page has useful content
        page_text = soup.get_text()
        has_ipo_data = any(
            w in page_text.lower() for w in ["issue price", "listing", "subscription"]
        )

        if not has_ipo_data and result.page_size_kb < 50:
            result.limitations.append(
                "Page appears to be a JavaScript shell — actual data is loaded "
                "dynamically via internal APIs. Direct HTML scraping will not work."
            )

        result.notes = (
            f"Page size: {result.page_size_kb:.0f} KB. "
            f"Tables found: {len(tables)}. "
            f"IPO data in static HTML: {'Yes' if has_ipo_data else 'No (JS-rendered)'}."
        )
        self.results.append(result)
        return result

    def test_bse_ipo_page(self) -> SourceTestResult:
        """
        Test BSE India IPO information page.
        BSE provides official listing and subscription data.
        """
        url = "https://www.bseindia.com/publicissue.html"
        result = SourceTestResult("BSE India IPO Page", url, "ipo_listing")
        logger.info(f"Testing: {result.source_name}")

        resp = self.client.get(url)
        result.http_status = resp["status_code"]
        result.response_time_ms = resp["elapsed_ms"]
        result.content_type = resp["content_type"]

        if not resp["success"]:
            result.error = resp["error"]
            result.limitations.append(f"BSE page returned: {resp['error']}")
            self.results.append(result)
            return result

        result.success = True
        html = resp["text"]
        result.page_size_kb = len(html) / 1024

        soup = self._parse_html(html)
        tables = soup.find_all("table")
        result.tables_found = len(tables)

        page_text = soup.get_text().lower()
        has_data = "ipo" in page_text or "issue" in page_text

        if not has_data:
            result.limitations.append(
                "BSE may load IPO data dynamically. "
                "Consider BSE APIs or alternative aggregator sources."
            )

        result.notes = (
            f"Page size: {result.page_size_kb:.0f} KB. "
            f"Tables found: {len(tables)}."
        )
        self.results.append(result)
        return result

    def test_chittorgarh_subscription(self) -> SourceTestResult:
        """
        Test Chittorgarh subscription data page.
        Subscription figures (QIB, NII, Retail) are critical for post-close models.
        """
        url = "https://www.chittorgarh.com/report/ipo-subscription-status-live-bidding-data/21/"
        result = SourceTestResult("Chittorgarh Subscription Status", url, "subscription")
        logger.info(f"Testing: {result.source_name}")

        resp = self.client.get(url)
        result.http_status = resp["status_code"]
        result.response_time_ms = resp["elapsed_ms"]
        result.content_type = resp["content_type"]

        if not resp["success"]:
            result.error = resp["error"]
            self.results.append(result)
            return result

        result.success = True
        html = resp["text"]
        result.page_size_kb = len(html) / 1024

        soup = self._parse_html(html)
        tables = soup.find_all("table")
        result.tables_found = len(tables)

        table_headers = self._extract_table_headers(soup)
        for i, headers in enumerate(table_headers[:3]):
            result.relevant_selectors.append(f"table[{i}]: {headers[:10]}")

        samples = self._extract_sample_rows(soup, max_tables=2, max_rows=3)
        if samples:
            result.sample_data = samples[0][:3]

        page_text = html.lower()
        sub_fields = {
            "qib": "qib" in page_text,
            "nii_hni": "nii" in page_text or "hni" in page_text,
            "retail": "retail" in page_text,
            "total_subscription": "total" in page_text and ("subscription" in page_text or "times" in page_text),
            "application_count": "application" in page_text,
        }
        result.data_fields_found = [k for k, v in sub_fields.items() if v]

        result.notes = f"Found {len(tables)} tables. Fields: {result.data_fields_found}"
        self.results.append(result)
        return result

    def test_chittorgarh_ipo_financials(self) -> SourceTestResult:
        """
        Test Chittorgarh individual IPO page for financial data.
        Financial metrics (revenue, profit, P/E) are available on detail pages.
        """
        url = "https://www.chittorgarh.com/ipo/tata-technologies-ipo/1577/"
        result = SourceTestResult("Chittorgarh IPO Financials (Tata Technologies)", url, "financials")
        logger.info(f"Testing: {result.source_name}")

        resp = self.client.get(url)
        result.http_status = resp["status_code"]
        result.response_time_ms = resp["elapsed_ms"]
        result.content_type = resp["content_type"]

        if not resp["success"]:
            result.error = resp["error"]
            self.results.append(result)
            return result

        result.success = True
        html = resp["text"]
        result.page_size_kb = len(html) / 1024

        soup = self._parse_html(html)
        tables = soup.find_all("table")
        result.tables_found = len(tables)

        table_headers = self._extract_table_headers(soup)
        for i, headers in enumerate(table_headers[:6]):
            result.relevant_selectors.append(f"table[{i}]: {headers[:8]}")

        page_text = html.lower()
        fin_fields = {
            "revenue": "revenue" in page_text,
            "profit": "profit" in page_text or "pat" in page_text,
            "ebitda": "ebitda" in page_text,
            "eps": "eps" in page_text,
            "pe_ratio": "p/e" in page_text or "pe " in page_text,
            "roe_ronw": "roe" in page_text or "ronw" in page_text,
            "nav": "nav" in page_text or "net asset" in page_text,
            "debt": "debt" in page_text or "borrowing" in page_text,
            "net_worth": "net worth" in page_text or "networth" in page_text,
            "peer_comparison": "peer" in page_text or "listed peer" in page_text,
        }
        result.data_fields_found = [k for k, v in fin_fields.items() if v]

        samples = self._extract_sample_rows(soup, max_tables=4, max_rows=2)
        if samples:
            result.sample_data = samples[0][:2]

        result.notes = (
            f"Found {len(tables)} tables. "
            f"Financial fields detected: {len(result.data_fields_found)}. "
            f"Page size: {result.page_size_kb:.0f} KB."
        )
        self.results.append(result)
        return result

    def test_sebi_offer_documents(self) -> SourceTestResult:
        """
        Test SEBI offer documents page.
        SEBI hosts official RHP/DRHP filings — the most authoritative source
        for IPO financial and structural data.
        """
        url = "https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=2&ssid=21&smession=No"
        result = SourceTestResult("SEBI Offer Documents", url, "rhp_drhp")
        logger.info(f"Testing: {result.source_name}")

        resp = self.client.get(url)
        result.http_status = resp["status_code"]
        result.response_time_ms = resp["elapsed_ms"]
        result.content_type = resp["content_type"]

        if not resp["success"]:
            result.error = resp["error"]
            result.limitations.append(
                "SEBI website may require specific request patterns. "
                "RHP PDFs may be accessible through direct filing links."
            )
            self.results.append(result)
            return result

        result.success = True
        html = resp["text"]
        result.page_size_kb = len(html) / 1024

        soup = self._parse_html(html)

        # Look for links to offer documents (PDFs)
        pdf_links = []
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            text = link.get_text(strip=True)
            if ".pdf" in href.lower() or "rhp" in text.lower() or "offer" in text.lower():
                pdf_links.append({"text": text[:80], "href": href[:120]})

        result.data_fields_found = ["pdf_links"] if pdf_links else []
        result.sample_data = pdf_links[:5]

        tables = soup.find_all("table")
        result.tables_found = len(tables)

        result.limitations.append("SEBI filings require navigating paginated lists.")
        result.limitations.append("Individual RHP PDFs can be 400-900+ pages and several hundred MB.")
        result.notes = (
            f"Page size: {result.page_size_kb:.0f} KB. "
            f"Tables: {len(tables)}. "
            f"PDF links found: {len(pdf_links)}."
        )
        self.results.append(result)
        return result

    def test_chittorgarh_ipo_archive(self) -> SourceTestResult:
        """
        Test Chittorgarh year-wise IPO archive.
        Historical data is needed to build the training dataset.
        """
        url = "https://www.chittorgarh.com/report/mainboard-ipo-list-in-india-702/82/"
        result = SourceTestResult("Chittorgarh Mainboard IPO Archive", url, "ipo_listing")
        logger.info(f"Testing: {result.source_name}")

        resp = self.client.get(url)
        result.http_status = resp["status_code"]
        result.response_time_ms = resp["elapsed_ms"]
        result.content_type = resp["content_type"]

        if not resp["success"]:
            result.error = resp["error"]
            self.results.append(result)
            return result

        result.success = True
        html = resp["text"]
        result.page_size_kb = len(html) / 1024

        soup = self._parse_html(html)
        tables = soup.find_all("table")
        result.tables_found = len(tables)

        table_headers = self._extract_table_headers(soup)
        for i, headers in enumerate(table_headers[:3]):
            result.relevant_selectors.append(f"table[{i}]: {headers[:12]}")

        samples = self._extract_sample_rows(soup, max_tables=2, max_rows=5)
        if samples:
            result.sample_data = samples[0][:5]

        # Try to count how many IPO rows are present
        ipo_rows = 0
        for table in tables:
            tbody = table.find("tbody")
            if tbody:
                rows = tbody.find_all("tr")
                if rows:
                    ipo_rows = max(ipo_rows, len(rows))

        result.notes = (
            f"Found {len(tables)} tables. "
            f"Largest table has ~{ipo_rows} data rows. "
            f"Page size: {result.page_size_kb:.0f} KB."
        )
        self.results.append(result)
        return result

    # ──────────────────────────────────────────────────────────────────────
    # Run all tests and generate report
    # ──────────────────────────────────────────────────────────────────────

    def run_all_tests(self) -> List[SourceTestResult]:
        """Execute all source tests in sequence with rate limiting between each."""
        logger.info("=" * 70)
        logger.info("IPOVision Phase 1 — Data Source Testing")
        logger.info("=" * 70)

        test_methods = [
            self.test_chittorgarh_ipo_listing,
            self.test_chittorgarh_ipo_detail,
            self.test_chittorgarh_gmp,
            self.test_chittorgarh_subscription,
            self.test_chittorgarh_ipo_financials,
            self.test_chittorgarh_ipo_archive,
            self.test_investorgain_ipo_listing,
            self.test_nse_past_issues,
            self.test_bse_ipo_page,
            self.test_sebi_offer_documents,
        ]

        for test_fn in test_methods:
            try:
                test_fn()
            except Exception as e:
                logger.error(f"Test {test_fn.__name__} failed with exception: {e}")
                # Still continue with other tests
                continue

        return self.results

    def generate_report(self, output_path: Optional[Path] = None) -> str:
        """
        Generate a structured JSON report of all test results.
        Saves to data/raw/source_test_report.json by default.
        """
        report = {
            "report_name": "IPOVision Phase 1 — Data Source Test Report",
            "generated_at": datetime.now().isoformat(),
            "total_sources_tested": len(self.results),
            "successful": sum(1 for r in self.results if r.success),
            "failed": sum(1 for r in self.results if not r.success),
            "results": [r.to_dict() for r in self.results],
        }

        if output_path is None:
            output_path = PROJECT_ROOT / "data" / "raw" / "source_test_report.json"

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"Report saved to: {output_path}")
        return json.dumps(report, indent=2, ensure_ascii=False)

    def print_summary(self) -> str:
        """Print a human-readable summary of test results to console."""
        lines = []
        lines.append("")
        lines.append("=" * 78)
        lines.append("  IPOVision Phase 1 — DATA SOURCE TEST SUMMARY")
        lines.append("=" * 78)

        # Group by category
        categories = {}
        for r in self.results:
            categories.setdefault(r.category, []).append(r)

        for category, results in categories.items():
            lines.append(f"\n{'─' * 78}")
            lines.append(f"  Category: {category.upper()}")
            lines.append(f"{'─' * 78}")

            for r in results:
                status = "✓ OK" if r.success else "✗ FAIL"
                lines.append(f"\n  [{status}] {r.source_name}")
                lines.append(f"    URL: {r.url}")
                lines.append(f"    HTTP: {r.http_status} | Time: {r.response_time_ms:.0f}ms" if r.response_time_ms else f"    HTTP: {r.http_status}")
                if r.page_size_kb:
                    lines.append(f"    Page size: {r.page_size_kb:.0f} KB | Tables: {r.tables_found}")
                if r.data_fields_found:
                    lines.append(f"    Fields found: {', '.join(r.data_fields_found)}")
                if r.relevant_selectors:
                    for sel in r.relevant_selectors[:3]:
                        lines.append(f"    Selector: {sel}")
                if r.sample_data:
                    lines.append(f"    Sample data ({len(r.sample_data)} rows):")
                    for row in r.sample_data[:2]:
                        # Truncate each value for display
                        short_row = {k: v[:40] if isinstance(v, str) and len(v) > 40 else v for k, v in row.items()}
                        lines.append(f"      {short_row}")
                if r.limitations:
                    lines.append(f"    Limitations:")
                    for lim in r.limitations:
                        lines.append(f"      - {lim}")
                if r.error:
                    lines.append(f"    Error: {r.error}")
                if r.notes:
                    lines.append(f"    Notes: {r.notes}")

        # Overall summary
        total = len(self.results)
        ok = sum(1 for r in self.results if r.success)
        fail = total - ok
        lines.append(f"\n{'=' * 78}")
        lines.append(f"  OVERALL: {ok}/{total} sources accessible ({fail} failed)")
        lines.append(f"{'=' * 78}")

        summary = "\n".join(lines)
        print(summary)
        return summary


def main():
    """Entry point for running the source test suite."""
    tester = IPOSourceTester()
    tester.run_all_tests()
    summary = tester.print_summary()
    report_json = tester.generate_report()

    # Save summary to a text file too
    summary_path = PROJECT_ROOT / "data" / "raw" / "source_test_summary.txt"
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(summary)
    logger.info(f"Summary saved to: {summary_path}")


if __name__ == "__main__":
    main()

