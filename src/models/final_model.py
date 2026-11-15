"""IPOVision final model (Phase 8).

Choice recorded from the evaluation harness (reports/evaluation/scoreboard_v3.md): the GMP-only logistic
regression is the benchmark and the production model; richer feature sets did not beat it on Brier
(paired intervals include 0) and had lower AUC. Without a GMP the subscription-only logistic is used,
and with neither the training base rate is returned.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

GMP_BUCKETS = ((-np.inf, 0.0, "GMP <= 0"), (0.0, 10.0, "GMP 0-10"), (10.0, 30.0, "GMP 10-30"), (30.0, np.inf, "GMP > 30"))
BAND_EDGES = (0.15, 0.40)            # on P(non-positive): Low < 0.15 <= Medium < 0.40 <= High
BAND_NAMES = ("Low", "Medium", "High")
INTERVAL = (0.10, 0.90)              # 80% interval from residual quantiles
GMP_CLIP = (-50.0, 200.0)
ZONE_LIMIT = 10.0


def bucket_name(gmp_pct: float) -> str:
    for lo, hi, name in GMP_BUCKETS:
        if lo < gmp_pct <= hi:
            return name
    return GMP_BUCKETS[0][2]


def band_labels(p_non_positive) -> np.ndarray:
    idx = np.digitize(np.asarray(p_non_positive, dtype=float), BAND_EDGES)
    return np.array(BAND_NAMES)[idx]


def _logit():
    return make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000))


def residual_quantiles(df: pd.DataFrame, q=INTERVAL, min_n: int = 15) -> Dict[str, Optional[dict]]:
    """Quantiles of (actual gain - GMP%) inside each GMP bucket."""
    res = df["listing_gain_pct"] - df["gmp_pct_of_issue"]
    out = {}
    for lo, hi, name in GMP_BUCKETS:
        r = res[(df["gmp_pct_of_issue"] > lo) & (df["gmp_pct_of_issue"] <= hi)]
        out[name] = ({"n": int(len(r)), "lo": float(r.quantile(q[0])), "hi": float(r.quantile(q[1]))}
                     if len(r) >= min_n else None)
    return out


def interval_coverage(frame: pd.DataFrame, test_years) -> pd.DataFrame:
    """Out-of-sample check: intervals built only from earlier years, scored on each test year."""
    rows = []
    for yr in test_years:
        tr, te = frame[frame["listing_year"] < yr], frame[frame["listing_year"] == yr]
        q = residual_quantiles(tr)
        for g, gain in zip(te["gmp_pct_of_issue"], te["listing_gain_pct"]):
            qq = q.get(bucket_name(g))
            if qq is None:
                continue
            rows.append({"year": yr, "bucket": bucket_name(g), "covered": bool(g + qq["lo"] <= gain <= g + qq["hi"]),
                         "width": qq["hi"] - qq["lo"]})
    return pd.DataFrame(rows)


def train(base: pd.DataFrame) -> dict:
    d = base.copy()
    d["y"] = (d["listing_gain_pct"] > 0).astype(int)
    g = d[d["gmp_pct_of_issue"].notna()]
    s = d[d["log_total"].notna()]
    if g["y"].nunique() < 2 or s["y"].nunique() < 2:
        raise ValueError("Training data needs both positive and non-positive listings.")
    dates = pd.to_datetime(d["listing_date"]) if "listing_date" in d.columns else None
    return {"version": "1.0", "trained_at": datetime.now().isoformat(timespec="seconds"),
            "n_gmp_rows": int(len(g)), "n_sub_rows": int(len(s)),
            "listing_dates": [str(dates.min().date()), str(dates.max().date())] if dates is not None else None,
            "model_gmp": _logit().fit(g[["gmp_pct_of_issue"]], g["y"]),
            "model_sub": _logit().fit(s[["log_total"]], s["y"]),
            "prior_positive": float(d["y"].mean()),
            "residual_quantiles": residual_quantiles(g)}


def predict(bundle: dict, gmp_pct: Optional[float] = None, total_sub: Optional[float] = None,
            issue_price: Optional[float] = None) -> dict:
    notes, interval = [], None
    gmp_ok = gmp_pct is not None and not pd.isna(gmp_pct)
    sub_ok = total_sub is not None and not pd.isna(total_sub) and total_sub > 0
    g = None
    if gmp_ok:
        g = float(np.clip(gmp_pct, *GMP_CLIP))
        p = float(bundle["model_gmp"].predict_proba(pd.DataFrame({"gmp_pct_of_issue": [g]}))[0, 1])
        model = "GMP logistic"
        q = bundle["residual_quantiles"].get(bucket_name(g))
        if q:
            interval = (g + q["lo"], g + q["hi"])
        if g <= ZONE_LIMIT:
            notes.append("GMP at or below 10%: outcomes in this zone have been close to a coin flip, "
                         "so treat this probability as weak evidence.")
    elif sub_ok:
        p = float(bundle["model_sub"].predict_proba(pd.DataFrame({"log_total": [np.log1p(total_sub)]}))[0, 1])
        model = "Subscription logistic (no GMP supplied)"
        notes.append("No GMP supplied: subscription alone is clearly weaker than GMP.")
    else:
        p, model = bundle["prior_positive"], "Historical base rate (no inputs)"
        notes.append("No inputs supplied: this is only the historical share of positive listings.")
    out = {"model_used": model, "p_positive": p, "p_non_positive": 1 - p,
           "band": str(band_labels([1 - p])[0]), "gmp_pct_used": g, "gain_interval_pct": interval,
           "implied_listing_price": None, "price_interval": None, "notes": notes}
    if issue_price and g is not None:
        out["implied_listing_price"] = issue_price * (1 + g / 100)
        if interval:
            out["price_interval"] = tuple(issue_price * (1 + v / 100) for v in interval)
    return out


def save_bundle(bundle: dict, path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, path)
    return path


def load_bundle(path) -> dict:
    return joblib.load(path)