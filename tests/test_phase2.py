"""
IPOVision — Phase 2 Automated Test Suite
========================================

Comprehensive validation and data engineering test suite testing:
- Canonical IPO identifier generation, formatting, and registry operations.
- Data cleaning routines (dates, numbers, subscriptions, company entity normalization).
- Leakage isolation (pre-close vs post-close subscription barriers).
- Temporal cutoff enforcement (feature timestamp <= data_cutoff).
- Unofficial sentiment policy (missing GMP remains NaN, synchronized gmp_missing flag).
- Ground truth listing outcome mathematics and classification target derivation.
- Edge cases: loss-making PAT, absent GMP, par listing (gain=0 -> positive=0), missing financials.
- Atomic dataset storage and duplicate detection.

Run:
    python -m pytest tests/test_phase2.py -v
    # or with standard unittest:
    python tests/test_phase2.py
"""

import os
import sys
import shutil
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from src.cleaning.ipo_id import (
    is_valid_ipo_id,
    parse_ipo_id,
    format_ipo_id,
    normalize_company_name,
    IPORegistryManager,
)
from src.cleaning.cleaner import IPOCleaner
from src.cleaning.validators import (
    validate_features_dataset,
    validate_outcomes_dataset,
    validate_gmp_history_dataset,
    validate_registry_dataset,
    validate_feature_sources_dataset,
    check_referential_integrity,
)
from src.cleaning.dataset_manager import DatasetManager

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"


class TestIPOIdSystem(unittest.TestCase):
    """Tests for the canonical IPO ID convention and master registry."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.registry_path = Path(self.temp_dir) / "ipo_registry.csv"
        self.registry = IPORegistryManager(registry_path=self.registry_path)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_id_format_regex(self):
        """Validates adherence to 'INMAIN-YYYY-NNNN'."""
        self.assertTrue(is_valid_ipo_id("INMAIN-2024-0001"))
        self.assertTrue(is_valid_ipo_id("INMAIN-2025-0123"))
        self.assertFalse(is_valid_ipo_id("2024-SWIGGY"))  # Old Phase 0 format
        self.assertFalse(is_valid_ipo_id("inmain-2024-0001"))  # Lowercase
        self.assertFalse(is_valid_ipo_id("INMAIN-24-0001"))  # 2-digit year
        self.assertFalse(is_valid_ipo_id("INMAIN-2024-1"))  # Unpadded sequence
        self.assertFalse(is_valid_ipo_id(""))
        self.assertFalse(is_valid_ipo_id(None))

    def test_parse_and_format_ipo_id(self):
        """Tests deconstructing and formatting IDs."""
        market, year, seq = parse_ipo_id("INMAIN-2024-0042")
        self.assertEqual(market, "INMAIN")
        self.assertEqual(year, 2024)
        self.assertEqual(seq, 42)

        formatted = format_ipo_id(2025, 7)
        self.assertEqual(formatted, "INMAIN-2025-0007")

        with self.assertRaises(ValueError):
            format_ipo_id(1850, 1)  # Invalid year
        with self.assertRaises(ValueError):
            format_ipo_id(2025, 0)  # Invalid sequence

    def test_normalize_company_name(self):
        """Tests entity name normalization for registry matching."""
        self.assertEqual(normalize_company_name("Swiggy Limited"), "SWIGGY")
        self.assertEqual(normalize_company_name("Tata Technologies Ltd."), "TATA TECHNOLOGIES")
        self.assertEqual(normalize_company_name("Hyundai Motor India Limited"), "HYUNDAI MOTOR")
        self.assertEqual(normalize_company_name("Bajaj Housing Finance Ltd"), "BAJAJ HOUSING FINANCE")

    def test_registry_registration_and_idempotence(self):
        """Tests atomic registration and idempotent ID retrieval."""
        id1 = self.registry.get_or_create_ipo_id(
            company_name="Swiggy Limited",
            year=2024,
            symbol="SWIGGY",
            issue_open_date="2024-11-06",
            issue_close_date="2024-11-08",
        )
        self.assertEqual(id1, "INMAIN-2024-0001")

        # Idempotent lookup with exact name
        id1_again = self.registry.get_or_create_ipo_id(
            company_name="Swiggy Limited",
            year=2024,
            symbol="SWIGGY",
        )
        self.assertEqual(id1_again, "INMAIN-2024-0001")

        # Second registration in same year increments sequence
        id2 = self.registry.get_or_create_ipo_id(
            company_name="Hyundai Motor India Limited",
            year=2024,
            symbol="HYUNDAIMOTOR",
        )
        self.assertEqual(id2, "INMAIN-2024-0002")

        # Registration in a different year resets sequence to 0001
        id_2025 = self.registry.get_or_create_ipo_id(
            company_name="Future Tech Limited",
            year=2025,
        )
        self.assertEqual(id_2025, "INMAIN-2025-0001")


class TestIPOCleaner(unittest.TestCase):
    """Tests for data cleaning, type conversion, and leakage neutralization."""

    def setUp(self):
        self.cleaner = IPOCleaner()

    def test_clean_number(self):
        """Tests numeric conversion from diverse financial string formats."""
        cn = IPOCleaner.clean_number
        self.assertEqual(cn("₹22.98 Cr"), 22.98)
        self.assertEqual(cn("1,234.56"), 1234.56)
        self.assertEqual(cn("₹111 per share"), 111.0)
        self.assertEqual(cn("15.5%"), 15.5)
        self.assertEqual(cn("-2,350.24"), -2350.24)  # Preserves loss!
        self.assertEqual(cn(42), 42.0)
        self.assertIsNone(cn("-"))
        self.assertIsNone(cn("--"))
        self.assertIsNone(cn("N/A"))
        self.assertIsNone(cn(""))
        self.assertIsNone(cn(None))

    def test_parse_subscription_multiple(self):
        """Tests parsing subscription multipliers with trailing text."""
        ps = IPOCleaner.parse_subscription_multiple
        self.assertEqual(ps("12.79x"), 12.79)
        self.assertEqual(ps("0.95x"), 0.95)
        self.assertEqual(ps("12.795th Nov"), 12.79)  # Ordinal date edge case
        self.assertEqual(ps("69.43"), 69.43)
        self.assertIsNone(ps("-"))
        self.assertIsNone(ps(None))

    def test_clean_date(self):
        """Tests parsing various date representations into YYYY-MM-DD."""
        cd = IPOCleaner.clean_date
        self.assertEqual(cd("2024-11-06"), "2024-11-06")
        self.assertEqual(cd("Wed, Dec 13, 2023"), "2023-12-13")
        self.assertEqual(cd("11 to 13 Mar, 2024"), "2024-03-11")
        self.assertEqual(cd("11-Nov", default_year=2024), "2024-11-11")
        self.assertIsNone(cd("-"))
        self.assertIsNone(cd(None))

    def test_leakage_neutralization_in_pre_close(self):
        """Verifies that clean_features_df physically clears subscriptions in pre_close."""
        raw_data = pd.DataFrame([
            {
                "ipo_id": "INMAIN-2024-0001",
                "prediction_stage": "pre_close",
                "overall_subscription": "15.4x",  # Leaked!
                "qib_subscription": "20.1",       # Leaked!
                "issue_price": "₹390 per share",
                "gmp": "₹25.0",
            },
            {
                "ipo_id": "INMAIN-2024-0001",
                "prediction_stage": "post_close",
                "overall_subscription": "15.4x",  # Allowed in post_close
                "qib_subscription": "20.1",       # Allowed in post_close
                "issue_price": "₹390 per share",
                "gmp": "₹25.0",
            },
        ])

        cleaned_df, log = self.cleaner.clean_features_df(raw_data)

        # Pre-close subscriptions must be forced to None/NaN
        self.assertTrue(pd.isna(cleaned_df.loc[0, "overall_subscription"]))
        self.assertTrue(pd.isna(cleaned_df.loc[0, "qib_subscription"]))

        # Post-close subscriptions must be preserved
        self.assertEqual(cleaned_df.loc[1, "overall_subscription"], 15.4)
        self.assertEqual(cleaned_df.loc[1, "qib_subscription"], 20.1)

    def test_gmp_missing_synchronization(self):
        """Verifies gmp_missing flag is 0 when GMP present, and 1 when absent."""
        df = pd.DataFrame([
            {"gmp": "₹25.0"},
            {"gmp": None},
            {"gmp": "-"},
        ])
        cleaned_df, _ = self.cleaner.clean_features_df(df)
        self.assertEqual(cleaned_df.loc[0, "gmp_missing"], 0)
        self.assertEqual(cleaned_df.loc[1, "gmp_missing"], 1)
        self.assertEqual(cleaned_df.loc[2, "gmp_missing"], 1)
        # Verify missing GMP was NOT filled with zero
        self.assertTrue(pd.isna(cleaned_df.loc[1, "gmp"]))


class TestValidators(unittest.TestCase):
    """Tests for dataset validation rules and leakage detection."""

    def test_synthetic_valid_fixtures(self):
        """Verifies that all primary synthetic fixtures pass validation."""
        features_df = pd.read_csv(FIXTURES_DIR / "synthetic_ipo_features.csv")
        outcomes_df = pd.read_csv(FIXTURES_DIR / "synthetic_ipo_outcomes.csv")
        gmp_df = pd.read_csv(FIXTURES_DIR / "synthetic_ipo_gmp_history.csv")
        registry_df = pd.read_csv(FIXTURES_DIR / "synthetic_ipo_registry.csv")
        sources_df = pd.read_csv(FIXTURES_DIR / "synthetic_ipo_feature_sources.csv")

        rep_feat = validate_features_dataset(features_df)
        self.assertTrue(rep_feat.is_valid, f"Features errors: {rep_feat.errors}")

        rep_out = validate_outcomes_dataset(outcomes_df)
        self.assertTrue(rep_out.is_valid, f"Outcomes errors: {rep_out.errors}")

        rep_gmp = validate_gmp_history_dataset(gmp_df)
        self.assertTrue(rep_gmp.is_valid, f"GMP errors: {rep_gmp.errors}")

        rep_reg = validate_registry_dataset(registry_df)
        self.assertTrue(rep_reg.is_valid, f"Registry errors: {rep_reg.errors}")

        rep_src = validate_feature_sources_dataset(sources_df)
        self.assertTrue(rep_src.is_valid, f"Sources errors: {rep_src.errors}")

    def test_detect_pre_close_subscription_leakage(self):
        """Validators must flag subscription data in pre_close as fatal error."""
        leaky_df = pd.DataFrame([{
            "ipo_id": "INMAIN-2024-0001",
            "company_name": "Test Co",
            "issue_open_date": "2024-11-01",
            "issue_close_date": "2024-11-03",
            "issue_price": 100.0,
            "issue_size_cr": 500.0,
            "prediction_stage": "pre_close",
            "data_cutoff": "2024-11-02T18:00:00",
            "overall_subscription": 5.4,  # FATAL LEAK!
        }])
        rep = validate_features_dataset(leaky_df)
        self.assertFalse(rep.is_valid)
        self.assertTrue(any("LOOK-AHEAD LEAKAGE" in str(e) for e in rep.errors))

    def test_detect_target_leakage_in_features(self):
        """Outcome columns in the feature dataset must fail validation."""
        target_leak_df = pd.DataFrame([{
            "ipo_id": "INMAIN-2024-0001",
            "company_name": "Test Co",
            "issue_open_date": "2024-11-01",
            "issue_close_date": "2024-11-03",
            "issue_price": 100.0,
            "issue_size_cr": 500.0,
            "prediction_stage": "post_close",
            "data_cutoff": "2024-11-04T18:00:00",
            "listing_gain_pct": 15.5,  # TARGET LEAK!
        }])
        rep = validate_features_dataset(target_leak_df)
        self.assertFalse(rep.is_valid)
        self.assertTrue(any("TARGET LEAKAGE" in str(e) for e in rep.errors))

    def test_detect_temporal_cutoff_violation(self):
        """Observations after the cutoff date must trigger temporal leakage error."""
        cutoff_leak_df = pd.DataFrame([{
            "ipo_id": "INMAIN-2024-0001",
            "company_name": "Test Co",
            "issue_open_date": "2024-11-01",
            "issue_close_date": "2024-11-03",
            "issue_price": 100.0,
            "issue_size_cr": 500.0,
            "prediction_stage": "pre_close",
            "data_cutoff": "2024-11-02T18:00:00",
            "gmp": 20.0,
            "gmp_missing": 0,
            "gmp_recorded_at": "2024-11-03T12:00:00",  # AFTER CUTOFF!
        }])
        rep = validate_features_dataset(cutoff_leak_df)
        self.assertFalse(rep.is_valid)
        self.assertTrue(any("TEMPORAL LEAKAGE" in str(e) for e in rep.errors))

    def test_detect_negative_debt_error(self):
        """Negative borrowings must be rejected."""
        neg_debt_df = pd.DataFrame([{
            "ipo_id": "INMAIN-2024-0001",
            "company_name": "Test Co",
            "issue_open_date": "2024-11-01",
            "issue_close_date": "2024-11-03",
            "issue_price": 100.0,
            "issue_size_cr": 500.0,
            "prediction_stage": "post_close",
            "data_cutoff": "2024-11-04T18:00:00",
            "total_debt": -50.0,  # IMPOSSIBLE
        }])
        rep = validate_features_dataset(neg_debt_df)
        self.assertFalse(rep.is_valid)
        self.assertTrue(any("total_debt cannot be negative" in str(e) for e in rep.errors))

    def test_outcomes_mathematical_consistency(self):
        """Listing gain % and listing_positive derivation verification."""
        # 1. Correct record
        good_outcomes = pd.DataFrame([{
            "ipo_id": "INMAIN-2024-0001",
            "listing_date": "2024-11-13",
            "issue_price": 100.0,
            "listing_open_price": 120.0,
            "listing_gain_pct": 20.0,
            "listing_positive": 1,
        }])
        self.assertTrue(validate_outcomes_dataset(good_outcomes).is_valid)

        # 2. Inconsistent gain %
        bad_gain = pd.DataFrame([{
            "ipo_id": "INMAIN-2024-0001",
            "listing_date": "2024-11-13",
            "issue_price": 100.0,
            "listing_open_price": 120.0,
            "listing_gain_pct": 5.0,  # Contradicts 20%!
            "listing_positive": 1,
        }])
        self.assertFalse(validate_outcomes_dataset(bad_gain).is_valid)

        # 3. Inconsistent classification target
        bad_pos = pd.DataFrame([{
            "ipo_id": "INMAIN-2024-0001",
            "listing_date": "2024-11-13",
            "issue_price": 100.0,
            "listing_open_price": 120.0,
            "listing_gain_pct": 20.0,
            "listing_positive": 0,  # Positive gain marked as 0!
        }])
        self.assertFalse(validate_outcomes_dataset(bad_pos).is_valid)

    def test_referential_integrity(self):
        """Foreign key validation across features and outcomes."""
        features_df = pd.DataFrame([{"ipo_id": "INMAIN-2024-0001"}])
        unmatched_outcomes = pd.DataFrame([{"ipo_id": "INMAIN-2024-0999"}])  # Unknown ID
        issues = check_referential_integrity(features_df, outcomes_df=unmatched_outcomes)
        self.assertTrue(any("does not exist in master registry/features" in str(i) for i in issues))


class TestEdgeCases(unittest.TestCase):
    """Verifies critical edge cases specified in Section 11 of Phase 2."""

    def test_edge_case_negative_pat_is_valid(self):
        """Startups with negative PAT (losses) must be allowed without validation error."""
        loss_df = pd.DataFrame([{
            "ipo_id": "INMAIN-2024-0004",
            "company_name": "LossMaking AI Limited",
            "issue_open_date": "2024-09-01",
            "issue_close_date": "2024-09-03",
            "issue_price": 250.0,
            "issue_size_cr": 400.0,
            "revenue": 55.0,
            "revenue_period": "FY2024",
            "profit_after_tax": -125.5,  # Legitimate startup loss!
            "pat_period": "FY2024",
            "prediction_stage": "pre_close",
            "data_cutoff": "2024-09-02T18:00:00",
        }])
        rep = validate_features_dataset(loss_df)
        self.assertTrue(rep.is_valid, f"Loss-making PAT caused unexpected error: {rep.errors}")

    def test_edge_case_missing_gmp_never_zero(self):
        """IPO with absent GMP is valid and retains NaN (never filled with 0.0)."""
        no_gmp_df = pd.DataFrame([{
            "ipo_id": "INMAIN-2024-0004",
            "company_name": "LossMaking AI Limited",
            "issue_open_date": "2024-09-01",
            "issue_close_date": "2024-09-03",
            "issue_price": 250.0,
            "issue_size_cr": 400.0,
            "gmp": None,  # Absent
            "gmp_missing": 1,
            "prediction_stage": "pre_close",
            "data_cutoff": "2024-09-02T18:00:00",
        }])
        rep = validate_features_dataset(no_gmp_df)
        self.assertTrue(rep.is_valid, f"Missing GMP caused unexpected error: {rep.errors}")

    def test_edge_case_par_listing_zero_gain(self):
        """Listing gain of exactly zero (open == issue) must derive listing_positive = 0."""
        zero_gain_outcomes = pd.DataFrame([{
            "ipo_id": "INMAIN-2024-0003",
            "listing_date": "2024-08-08",
            "issue_price": 100.0,
            "listing_open_price": 100.0,  # Exact par listing
            "listing_gain_pct": 0.0,
            "listing_positive": 0,  # Strictly 0 (not positive!)
        }])
        rep = validate_outcomes_dataset(zero_gain_outcomes)
        self.assertTrue(rep.is_valid, f"Par listing caused unexpected error: {rep.errors}")


class TestDatasetManager(unittest.TestCase):
    """Tests for DatasetManager I/O, atomic writing, and quality reporting."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.manager = DatasetManager(processed_dir=self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_atomic_save_and_load(self):
        """Saves a dataset atomically and verifies round-trip fidelity."""
        df = pd.DataFrame([
            {"ipo_id": "INMAIN-2024-0001", "company_name": "Swiggy Limited"},
            {"ipo_id": "INMAIN-2024-0002", "company_name": "Hyundai Motor"},
        ])
        path = self.manager.save_dataset(df, "ipo_registry", atomic=True)
        self.assertTrue(path.exists())
        self.assertFalse(path.with_suffix(".tmp").exists())  # Tmp file cleaned up

        loaded_df = self.manager.load_dataset("ipo_registry")
        self.assertEqual(len(loaded_df), 2)
        self.assertEqual(loaded_df.loc[0, "ipo_id"], "INMAIN-2024-0001")

    def test_duplicate_detection(self):
        """Verifies duplicate checking logic."""
        df_dups = pd.DataFrame([
            {"ipo_id": "INMAIN-2024-0001", "prediction_stage": "pre_close", "data_cutoff": "2024-11-01T18:00:00"},
            {"ipo_id": "INMAIN-2024-0001", "prediction_stage": "pre_close", "data_cutoff": "2024-11-01T18:00:00"},  # Duplicate
            {"ipo_id": "INMAIN-2024-0001", "prediction_stage": "post_close", "data_cutoff": "2024-11-03T18:00:00"},
        ])
        dups = self.manager.check_duplicates("ipo_features", df=df_dups)
        self.assertEqual(len(dups), 2)

    def test_data_quality_report_generation(self):
        """Generates quality report in temp directory."""
        rep_file = Path(self.temp_dir) / "quality_report.md"
        res = self.manager.generate_data_quality_report(output_path=rep_file)
        self.assertTrue(rep_file.exists())
        content = rep_file.read_text(encoding="utf-8")
        self.assertIn("IPOVision — Data Quality & Integrity Report", content)
        self.assertIn("ipo_features", content)


class TestEmptyTemplatesInProcessed(unittest.TestCase):
    """Verifies that the canonical processed CSV files are templates (0 rows)."""

    def test_all_five_templates_exist_and_empty(self):
        processed_dir = PROJECT_ROOT / "data" / "processed"
        expected_templates = [
            "ipo_features.csv",
            "ipo_outcomes.csv",
            "ipo_gmp_history.csv",
            "ipo_feature_sources.csv",
            "ipo_registry.csv",
        ]
        for fname in expected_templates:
            fpath = processed_dir / fname
            self.assertTrue(fpath.exists(), f"Missing template: {fpath}")
            df = pd.read_csv(fpath)
            self.assertEqual(len(df), 0, f"Template {fname} should have 0 data rows, found {len(df)}")
            self.assertGreater(len(df.columns), 0, f"Template {fname} should have header columns")


if __name__ == "__main__":
    unittest.main(verbosity=2)
