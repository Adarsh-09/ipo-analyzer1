import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.cleaning import DatasetManager, validate_features_dataset


class TestRound2Rules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        dm = DatasetManager()
        cls.f = dm.load_dataset("ipo_features")
        cls.r = dm.load_dataset("ipo_registry")
        cls.sample = cls.f[cls.f["gmp"].notna()].head(5).reset_index(drop=True)

    def test_every_row_is_listing_eve_with_cutoff_before_listing(self):
        self.assertTrue((self.f["prediction_stage"] == "listing_eve").all())
        self.assertTrue((pd.to_datetime(self.f["data_cutoff"]) < pd.to_datetime(self.f["listing_date"])).all())

    def test_listing_eve_accepts_untimestamped_gmp(self):
        self.assertEqual(validate_features_dataset(self.sample).error_count, 0)

    def test_post_close_rejects_untimestamped_gmp(self):
        rep = validate_features_dataset(self.sample.assign(prediction_stage="post_close"))
        self.assertGreater(rep.error_count, 0)
        self.assertTrue(any("listing_eve" in str(e) for e in rep.errors))

    def test_pre_close_still_rejects_subscription(self):
        rep = validate_features_dataset(self.sample.assign(prediction_stage="pre_close"))
        self.assertTrue(any("LOOK-AHEAD" in str(e) for e in rep.errors))

    def test_unit_price_above_limit_is_rejected(self):
        bad = self.sample.head(1).copy()
        bad["issue_price"] = 1_050_000.0
        rep = validate_features_dataset(bad)
        self.assertTrue(any(e.field == "issue_price" for e in rep.errors))

    def test_no_issue_price_above_limit_in_store(self):
        self.assertLessEqual(self.f["issue_price"].max(), 10000)

    def test_no_reit_like_names_in_registry(self):
        names = self.r["company_name"].str.lower()
        self.assertFalse(names.str.contains(r"\binvit\b|\breit\b|propshare|property share", regex=True).any())

    def test_same_date_and_price_ipos_do_not_share_a_gmp(self):
        g = self.f.dropna(subset=["gmp"]).groupby(["listing_date", "issue_price"])["gmp"].agg(["size", "nunique"])
        bad = g[(g["size"] > 1) & (g["nunique"] == 1)]
        self.assertTrue(bad.empty, f"Possible GMP join collision:\n{bad}")