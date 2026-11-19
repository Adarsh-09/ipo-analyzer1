import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.fundamental_analysis.scoring import (
    FUNDAMENTAL_BANDS,
    FUNDAMENTAL_WEIGHTS,
    LISTING_WEIGHTS,
    FundamentalInputs,
    ListingInputs,
    band_for,
    cagr,
    interp,
    score_fundamental,
    score_listing,
    fundamental_inputs_from_evidence,
    validate_fundamental_inputs,
)


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

class TestRhpEvidenceMapping(unittest.TestCase):

    @staticmethod
    def approved(value, unit=""):

        return {
            "value": value,
            "unit": unit,
            "status": "verified",
            "approved": True,
            "confidence": 0.95,
            "evidence": [{
                "page": 100,
                "quote": "Verified source quotation."
            }]
        }


    def test_unapproved_revenue_is_not_mapped(self):

        fields = {

            "revenue": {
                **self.approved([
                    {"period": "FY2023", "amount": 500},
                    {"period": "FY2024", "amount": 650}
                ]),
                "approved": False
            }

        }

        inputs, warnings = fundamental_inputs_from_evidence(
            fields
        )

        self.assertIsNone(inputs.revenue)


    def test_approved_revenue_and_pat_are_mapped(self):

        fields = {

            "revenue": self.approved([
                {"period": "FY2023", "amount": 500},
                {"period": "FY2024", "amount": 650},
                {"period": "FY2025", "amount": 850}
            ]),

            "pat": self.approved([
                {"period": "FY2023", "amount": 40},
                {"period": "FY2024", "amount": 60},
                {"period": "FY2025", "amount": 95}
            ])

        }

        inputs, warnings = fundamental_inputs_from_evidence(
            fields
        )

        self.assertEqual(
            inputs.revenue,
            [500.0, 650.0, 850.0]
        )

        self.assertEqual(
            inputs.pat,
            [40.0, 60.0, 95.0]
        )


    def test_mismatched_financial_periods_are_rejected(self):

        fields = {

            "revenue": self.approved([
                {"period": "FY2023", "amount": 500},
                {"period": "FY2024", "amount": 650}
            ]),

            "pat": self.approved([
                {"period": "FY2022", "amount": 30},
                {"period": "FY2023", "amount": 40}
            ])

        }

        inputs, warnings = fundamental_inputs_from_evidence(
            fields
        )

        self.assertIsNone(inputs.revenue)
        self.assertIsNone(inputs.pat)

        self.assertTrue(
            any("periods do not match" in x for x in warnings)
        )


    def test_derived_financial_metrics(self):

        fields = {

            "revenue": self.approved([
                {"period": "FY2024", "amount": 500},
                {"period": "FY2025", "amount": 600}
            ]),

            "ebitda": self.approved([
                {"period": "FY2024", "amount": 100},
                {"period": "FY2025", "amount": 120}
            ]),

            "total_borrowings": self.approved([
                {"period": "FY2024", "amount": 150},
                {"period": "FY2025", "amount": 180}
            ]),

            "net_worth": self.approved([
                {"period": "FY2024", "amount": 500},
                {"period": "FY2025", "amount": 600}
            ]),

            "fresh_issue_amount": self.approved(
                {"amount": 600, "unit": "INR crore"}
            ),

            "ofs_amount": self.approved(
                {"amount": 400, "unit": "INR crore"}
            )

        }

        inputs, warnings = fundamental_inputs_from_evidence(
            fields
        )

        self.assertAlmostEqual(
            inputs.ebitda_margin_pct,
            20.0
        )

        self.assertAlmostEqual(
            inputs.debt_to_equity,
            0.30
        )

        self.assertAlmostEqual(
            inputs.ofs_pct,
            40.0
        )


    def test_manual_override_takes_precedence(self):

        fields = {

            "roe_pct": self.approved(18)

        }

        inputs, warnings = fundamental_inputs_from_evidence(
            fields,
            manual_overrides={
                "roe_pct": 21
            }
        )

        self.assertEqual(
            inputs.roe_pct,
            21
        )


    def test_invalid_pledge_percentage_is_rejected(self):

        inputs = FundamentalInputs(
            promoter_pledge_pct=120
        )

        errors = validate_fundamental_inputs(
            inputs
        )

        self.assertTrue(
            any(
                "promoter_pledge_pct" in error
                for error in errors
            )
        )

        with self.assertRaises(ValueError):

            score_fundamental(inputs)

if __name__ == "__main__":
    unittest.main()