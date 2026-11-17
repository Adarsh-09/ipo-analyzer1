import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.fundamental_analysis.scoring import (FUNDAMENTAL_BANDS, FUNDAMENTAL_WEIGHTS, LISTING_WEIGHTS,
                                              FundamentalInputs, ListingInputs, band_for, cagr, interp,
                                              score_fundamental, score_listing)


class TestHelpers(unittest.TestCase):
    def test_weights_sum_to_100(self):
        self.assertEqual(sum(FUNDAMENTAL_WEIGHTS.values()), 100)
        self.assertEqual(sum(LISTING_WEIGHTS.values()), 100)

    def test_interp(self):
        pts = [(0, 0.0), (10, 1.0)]
        self.assertEqual(interp(-5, pts), 0.0); self.assertEqual(interp(20, pts), 1.0)
        self.assertAlmostEqual(interp(5, pts), 0.5)
        self.assertAlmostEqual(interp(1, [(0, 1.0), (2, 0.0)]), 0.5)        # decreasing scores work
        self.assertIsNone(interp(None, pts)); self.assertIsNone(interp(float("nan"), pts))

    def test_cagr(self):
        self.assertAlmostEqual(cagr([100, 110, 121]), 10.0, places=6)
        self.assertIsNone(cagr([-5, 10])); self.assertIsNone(cagr([100]))

    def test_band_edges(self):
        self.assertEqual(band_for(80, FUNDAMENTAL_BANDS), "Excellent")
        self.assertEqual(band_for(79.99, FUNDAMENTAL_BANDS), "Good")
        self.assertEqual(band_for(49.9, FUNDAMENTAL_BANDS), "Avoid / caution")


class TestListingScore(unittest.TestCase):
    def test_empty_input_has_no_score(self):
        r = score_listing(ListingInputs())
        self.assertIsNone(r["score"]); self.assertEqual(r["coverage"], 0.0)

    def test_strong_and_weak_setups(self):
        strong = score_listing(ListingInputs(gmp_pct=60, qib_sub=100, total_sub=150, nifty_ret_20d=6, issue_size_cr=500))
        weak = score_listing(ListingInputs(gmp_pct=-5, qib_sub=0.5, total_sub=0.8, nifty_ret_20d=-6, issue_size_cr=5000))
        self.assertGreaterEqual(strong["score"], 90); self.assertEqual(strong["band"], "Strong listing setup")
        self.assertLess(weak["score"], 25); self.assertEqual(weak["band"], "Weak")

    def test_score_rises_with_gmp(self):
        s = [score_listing(ListingInputs(gmp_pct=g, total_sub=5))["score"] for g in (-5, 5, 20, 50)]
        self.assertEqual(s, sorted(s)); self.assertLess(s[0], s[-1])

    def test_missing_inputs_are_not_zero(self):
        r = score_listing(ListingInputs(gmp_pct=60))
        self.assertGreaterEqual(r["score"], 95)                              # rescaled over the weight that exists
        self.assertAlmostEqual(r["coverage"], 0.30); self.assertTrue(r["partial"])


class TestFundamentalScore(unittest.TestCase):
    GOOD = dict(revenue=[500, 650, 850], pat=[40, 60, 95], ebitda_margin_pct=22, roe_pct=22, roce_pct=24,
                debt_to_equity=0.3, interest_coverage=9, cfo=90, inventory_days=60, inventory_days_prev=58,
                business_quality_rating=5, management_rating=5, promoter_holding_post_pct=70, promoter_pledge_pct=0,
                litigation_severity=0, peer_ebitda_margin_pct=15, peer_roe_pct=15, peer_revenue_growth_pct=15,
                pe_ratio=25, peer_pe_ratio=30, ofs_pct=10, use_of_funds_rating=4)

    def test_strong_company_scores_high_with_no_flags(self):
        r = score_fundamental(FundamentalInputs(**self.GOOD))
        self.assertGreaterEqual(r["score"], 85); self.assertEqual(r["band"], "Excellent")
        self.assertEqual(r["red_flags"], []); self.assertAlmostEqual(r["coverage"], 1.0)

    def test_red_flags(self):
        r = score_fundamental(FundamentalInputs(revenue=[100, 130, 170], pat=[20, 18, 15], debt_to_equity=3, cfo=2,
                                                ofs_pct=80, promoter_pledge_pct=20, litigation_severity=5,
                                                pe_ratio=60, peer_pe_ratio=30, inventory_days=100,
                                                inventory_days_prev=60))
        text = " ".join(r["red_flags"])
        for phrase in ("profits are flat or falling", "High debt", "offer for sale", "pledged", "litigation",
                       "well above listed peers", "cash flow"):
            self.assertIn(phrase, text)

    def test_partial_coverage_and_loss_making(self):
        r = score_fundamental(FundamentalInputs(pat=[-5, -3]))
        self.assertTrue(r["partial"]); self.assertEqual(r["categories"]["Revenue and profit growth"]["score"], 0.0)
        self.assertIn("Loss-making in the latest year.", r["red_flags"])
        self.assertIsNone(score_fundamental(FundamentalInputs())["score"])


if __name__ == "__main__":
    unittest.main()