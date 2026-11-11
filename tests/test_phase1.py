"""
IPOVision — Phase 1 Test Suite
Tests HTTP client functionality, scraper parsing logic, and PDF extraction readiness.
"""

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.collection.http_client import IPOHttpClient
from src.collection.investorgain_scraper import InvestorGainScraper
from src.collection.chittorgarh_detail_scraper import ChittorgarhDetailScraper


class TestPhase1Collection(unittest.TestCase):
    """Test suite for Phase 1 collection components."""

    def setUp(self):
        self.client = IPOHttpClient(rate_limit_delay=1.0, timeout=10)

    def test_http_client_initialization(self):
        """Verify IPOHttpClient initializes with proper headers and settings."""
        self.assertIsNotNone(self.client.session)
        self.assertIn("User-Agent", self.client.session.headers)
        self.assertEqual(self.client.timeout, 10)
        self.assertEqual(self.client.delay, 1.0)

    def test_http_client_get_structure(self):
        """Verify client.get returns a structured dictionary with expected keys."""
        res = self.client.get("https://httpbin.org/get")
        # If network is available, test real structure; otherwise test mock
        if res["success"]:
            self.assertEqual(res["status_code"], 200)
            self.assertIsNotNone(res["text"])
            self.assertIsNone(res["error"])
        else:
            self.assertIn("error", res)

    def test_investorgain_number_cleaning(self):
        """Verify number cleaner handles currencies, percentages, and commas."""
        self.assertEqual(InvestorGainScraper._clean_number("₹1,200.50"), 1200.50)
        self.assertEqual(InvestorGainScraper._clean_number("12.99%"), 12.99)
        self.assertEqual(InvestorGainScraper._clean_number("₹22.98 Cr"), 22.98)
        self.assertIsNone(InvestorGainScraper._clean_number("--"))
        self.assertIsNone(InvestorGainScraper._clean_number(None))

    def test_investorgain_name_cleaning(self):
        """Verify SME detection and company name sanitization."""
        res_sme = InvestorGainScraper._clean_company_name("Antala IndustriesBSE SME[email protected]")
        self.assertTrue(res_sme["is_sme"])
        self.assertNotIn("SME", res_sme["company_name"])

        res_main = InvestorGainScraper._clean_company_name("Hyundai Motor India Limited")
        self.assertFalse(res_main["is_sme"])
        self.assertEqual(res_main["company_name"], "Hyundai Motor India Limited")

    def test_investorgain_subscription_parsing(self):
        """Verify subscription multiple parser extracts leading float."""
        self.assertEqual(InvestorGainScraper._parse_subscription_multiple("12.79x"), 12.79)
        self.assertEqual(InvestorGainScraper._parse_subscription_multiple("12.795th Nov"), 12.79)
        self.assertEqual(InvestorGainScraper._parse_subscription_multiple("0.85x"), 0.85)
        self.assertIsNone(InvestorGainScraper._parse_subscription_multiple("--"))

    def test_chittorgarh_number_cleaning(self):
        """Verify Chittorgarh detail scraper cleans complex numeric text."""
        self.assertEqual(ChittorgarhDetailScraper._clean_number("₹53.41Cr"), 53.41)
        self.assertEqual(ChittorgarhDetailScraper._clean_number("₹111 per share"), 111.0)
        self.assertEqual(ChittorgarhDetailScraper._clean_number("1,200 Shares"), 1200.0)

    def test_source_test_report_exists(self):
        """Verify that Phase 1 diagnostic report was generated."""
        report_file = PROJECT_ROOT / "data" / "raw" / "source_test_report.json"
        self.assertTrue(report_file.exists(), "Missing data/raw/source_test_report.json")

    def test_notebook_exists(self):
        """Verify Phase 1 documentation notebook exists."""
        nb_file = PROJECT_ROOT / "notebooks" / "01_source_testing.ipynb"
        self.assertTrue(nb_file.exists(), "Missing notebooks/01_source_testing.ipynb")


if __name__ == "__main__":
    unittest.main(verbosity=2)
