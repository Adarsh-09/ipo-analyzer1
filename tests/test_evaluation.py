import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.evaluation.harness import (apply_labels, bootstrap_deltas, ece, flag_metrics,
                                    precision_at_recall, walk_forward)


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
        col = "p::A GMP only"
        a = bootstrap_deltas(pred, col, col, n_boot=100, seed=7)
        b = bootstrap_deltas(pred, col, col, n_boot=100, seed=7)
        self.assertEqual(a, b)
        self.assertEqual((a["dAUC"], a["dBrier"]), (0.0, 0.0))

    def test_clear_only_drops_flat_listings(self):
        d = make_frame()
        d.loc[:9, "listing_gain_pct"] = 1.0
        self.assertTrue((apply_labels(d, "clear_only")["listing_gain_pct"].abs() > 2.0).all())
        self.assertEqual(len(apply_labels(d, "strict")), len(d))


if __name__ == "__main__":
    unittest.main()