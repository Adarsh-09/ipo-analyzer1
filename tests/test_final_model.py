import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.models.final_model import (bucket_name, interval_coverage, load_bundle, predict, save_bundle, train)


def make_base(n=800, seed=0):
    rng = np.random.default_rng(seed)
    gmp = rng.normal(15, 25, n)
    d = pd.DataFrame({"listing_date": pd.to_datetime("2020-01-01") + pd.to_timedelta(rng.integers(0, 2500, n), unit="D"),
                      "gmp_pct_of_issue": gmp, "listing_gain_pct": gmp + rng.normal(0, 8, n),
                      "log_total": np.log1p(np.exp(rng.normal(2.5, 1.2, n)))})
    d["listing_year"] = d["listing_date"].dt.year
    return d


class TestFinalModel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = make_base()
        cls.bundle = train(cls.base)

    def test_probability_rises_with_gmp(self):
        p = [predict(self.bundle, gmp_pct=g)["p_positive"] for g in (-20, 5, 40)]
        self.assertLess(p[0], p[1]); self.assertLess(p[1], p[2])

    def test_risk_bands(self):
        self.assertEqual(predict(self.bundle, gmp_pct=-30)["band"], "High")
        self.assertEqual(predict(self.bundle, gmp_pct=60)["band"], "Low")

    def test_fallbacks(self):
        self.assertIn("Subscription", predict(self.bundle, total_sub=80)["model_used"])
        r = predict(self.bundle)
        self.assertIn("base rate", r["model_used"])
        self.assertAlmostEqual(r["p_positive"], self.bundle["prior_positive"])

    def test_interval_and_price(self):
        r = predict(self.bundle, gmp_pct=20, issue_price=100)
        lo, hi = r["gain_interval_pct"]
        self.assertLess(lo, 20); self.assertGreater(hi, 20)
        self.assertAlmostEqual(r["implied_listing_price"], 120.0)
        self.assertLess(r["price_interval"][0], r["price_interval"][1])

    def test_extreme_gmp_is_clipped(self):
        self.assertEqual(predict(self.bundle, gmp_pct=1e6)["p_positive"], predict(self.bundle, gmp_pct=200)["p_positive"])

    def test_bucket_edges(self):
        self.assertEqual(bucket_name(0.0), "GMP <= 0"); self.assertEqual(bucket_name(0.01), "GMP 0-10")
        self.assertEqual(bucket_name(10.0), "GMP 0-10"); self.assertEqual(bucket_name(10.01), "GMP 10-30")
        self.assertEqual(bucket_name(55), "GMP > 30")

    def test_save_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = save_bundle(self.bundle, Path(tmp) / "m.joblib")
            self.assertEqual(predict(load_bundle(path), gmp_pct=12)["p_positive"],
                             predict(self.bundle, gmp_pct=12)["p_positive"])

    def test_interval_coverage_is_near_80_percent(self):
        cov = interval_coverage(self.base, range(2022, 2027))["covered"].mean()
        self.assertTrue(0.70 <= cov <= 0.90, cov)


if __name__ == "__main__":
    unittest.main()