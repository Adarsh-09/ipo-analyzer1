import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.evaluation.harness import (
    apply_labels,
    bootstrap_deltas,
    ece,
    flag_metrics,
    precision_at_recall,
    walk_forward,
    add_gmp_transform,
    REF,
    ASINH_MODEL,
)


def make_frame(seed=0, n=420):
    rng = np.random.default_rng(seed)
    dates = pd.to_datetime("2020-01-01") + pd.to_timedelta(rng.integers(0, 365 * 7, n), unit="D")
    gmp = rng.normal(15, 20, n)
    y = (rng.random(n) < 1 / (1 + np.exp(-(gmp - 2) / 8))).astype(int)
    d = pd.DataFrame({"listing_date": dates, "company_name": [f"co{i}" for i in range(n)], "issue_price": 100.0,
                      "gmp_pct_of_issue": gmp, "log_total": rng.normal(3, 1, n), "log_issue_size": rng.normal(6, 1, n),
                      "nifty_ret_20d": rng.normal(0, 3, n), "recent_gain_mean10": rng.normal(15, 5, n),
                      "listing_gain_pct": np.where(y == 1, rng.random(n) * 30 + 0.5, -rng.random(n) * 30 - 0.5), "y": y})
    d["listing_year"] = d["listing_date"].dt.year
    d["quarter"] = d["listing_date"].dt.to_period("Q").astype(str)
    return d.sort_values("listing_date").reset_index(drop=True)


class TestHarness(unittest.TestCase):
    def test_walk_forward_trains_only_on_earlier_data(self):
        pred, folds = walk_forward(make_frame())
        self.assertFalse(folds.empty)
        self.assertTrue((folds["train_max_date"] < folds["test_min_date"]).all())
        self.assertTrue(set(pred["listing_year"]) <= set(range(2022, 2027)))
        self.assertTrue(pred.filter(like="p::").apply(lambda c: c.between(0, 1)).all().all())

    def test_ece_small_for_calibrated_probabilities(self):
        rng = np.random.default_rng(1)
        p = rng.random(20000)
        self.assertLess(ece((rng.random(20000) < p).astype(int), p), 0.02)

    def test_flag_metrics_and_precision_at_recall(self):
        y = np.array([0] * 10 + [1] * 90)
        p = np.concatenate([np.linspace(0.05, 0.2, 10), np.linspace(0.6, 0.95, 90)])
        m = flag_metrics(y, p, 0.10)
        self.assertEqual((m["recall_neg"], m["precision_neg"]), (1.0, 1.0))
        r = precision_at_recall(np.array([0, 0, 1, 1]), np.array([0.1, 0.2, 0.8, 0.9]), recall=1.0)
        self.assertEqual((r["flag_rate"], r["precision_neg"]), (0.5, 1.0))

    def test_bootstrap_is_reproducible_and_zero_for_identical_models(self):
        pred, _ = walk_forward(make_frame())
        col = f"p::{REF}"

        a = bootstrap_deltas(
            pred,
            col,
            col,
            n_boot=100,
            seed=7,
            by="quarter"
        )

        b = bootstrap_deltas(
            pred,
            col,
            col,
            n_boot=100,
            seed=7,
            by="quarter"
        )

        self.assertEqual(a, b)

        for metric in [
            "dAUC",
            "dPR_AUC_neg",
            "dBrier",
            "dLogloss",
            "dECE"
        ]:
            self.assertAlmostEqual(a[metric], 0.0)
            self.assertAlmostEqual(a[f"{metric}_lo"], 0.0)
            self.assertAlmostEqual(a[f"{metric}_hi"], 0.0)

    def test_clear_only_drops_flat_listings(self):
        d = make_frame()
        d.loc[:9, "listing_gain_pct"] = 1.0
        self.assertTrue((apply_labels(d, "clear_only")["listing_gain_pct"].abs() > 2.0).all())
        self.assertEqual(len(apply_labels(d, "strict")), len(d))

    def test_asinh_transform_preserves_sign_zero_and_order(self):
        frame = pd.DataFrame({
            "gmp_pct_of_issue": [
                -100,
                -50,
                -10,
                0,
                10,
                50,
                100
            ]
        })

        transformed = add_gmp_transform(frame)
        values = transformed["gmp_asinh10"].to_numpy()

        self.assertEqual(values[3], 0.0)
        self.assertTrue(np.all(np.diff(values) > 0))
        self.assertTrue(
            np.all(
                np.sign(frame["gmp_pct_of_issue"])
                == np.sign(values)
            )
        )

        # The raw feature must remain unchanged.
        np.testing.assert_array_equal(
            frame["gmp_pct_of_issue"].to_numpy(),
            transformed["gmp_pct_of_issue"].to_numpy()
        )

    def test_walk_forward_generates_asinh_predictions(self):
        frame = make_frame()
        pred, _ = walk_forward(frame)

        raw_col = f"p::{REF}"
        asinh_col = f"p::{ASINH_MODEL}"

        self.assertIn(raw_col, pred.columns)
        self.assertIn(asinh_col, pred.columns)
        self.assertEqual(
            len(pred[raw_col]),
            len(pred[asinh_col])
        )
        self.assertTrue(pred[asinh_col].notna().all())
        self.assertTrue(pred[asinh_col].between(0, 1).all())

    def test_raw_and_asinh_use_identical_walk_forward_rows(self):
        frame = make_frame()
        pred, folds = walk_forward(frame)

        self.assertEqual(
            len(pred),
            int(folds["n_test"].sum())
        )
        self.assertTrue(
            pred["listing_year"].isin(
                range(2022, 2027)
            ).all()
        )

    def test_quarter_bootstrap_reports_all_metrics(self):
        pred, _ = walk_forward(make_frame())
        result = bootstrap_deltas(
            pred,
            f"p::{REF}",
            f"p::{ASINH_MODEL}",
            n_boot=200,
            seed=42,
            by="quarter"
        )

        expected = [
            "dAUC",
            "dPR_AUC_neg",
            "dBrier",
            "dLogloss",
            "dECE",
        ]

        for metric in expected:
            self.assertIn(metric, result)
            self.assertIn(f"{metric}_lo", result)
            self.assertIn(f"{metric}_hi", result)
            self.assertLessEqual(
                result[f"{metric}_lo"],
                result[f"{metric}_hi"]
            )

        self.assertGreater(result["reps"], 0)

    def test_invalid_gmp_values_are_rejected(self):
        frame = pd.DataFrame({
            "gmp_pct_of_issue": [
                10.0,
                np.inf
            ]
        })

        with self.assertRaises(ValueError):
            add_gmp_transform(frame)


if __name__ == "__main__":
    unittest.main()