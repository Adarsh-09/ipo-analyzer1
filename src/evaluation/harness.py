"""IPOVision evaluation harness (improvement tracker B1-B4).

One place defines the rows, the folds, the baselines and the metrics, so every model is
compared on identical data and every number in a report comes from one command.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

REF = "A GMP only"

ASINH_MODEL = "A2 GMP asinh/10"

SPECS: Dict[str, List[str]] = {
    "A GMP only": ["gmp_pct_of_issue"],

    # Same LogisticRegression algorithm, different GMP representation.
    ASINH_MODEL: ["gmp_asinh10"],

    "S subscription only": ["log_total"],
    "B GMP + subscription": ["gmp_pct_of_issue", "log_total"],
    "C B + size + market + momentum": [
        "gmp_pct_of_issue",
        "log_total",
        "log_issue_size",
        "nifty_ret_20d",
        "recent_gain_mean10"
    ],
    "D C without GMP": [
        "log_total",
        "log_issue_size",
        "nifty_ret_20d",
        "recent_gain_mean10"
    ],
    "E size + market + momentum": [
        "log_issue_size",
        "nifty_ret_20d",
        "recent_gain_mean10"
    ],
}
FLAG_RATES = (0.20, 0.35, 0.50)
FLAT_BAND = 2.0
ZONES = {
    "all": lambda g: g > -np.inf,
    "GMP <= 0": lambda g: g <= 0,
    "GMP 0-10": lambda g: (g > 0) & (g <= 10),
    "GMP > 10": lambda g: g > 10,
    "GMP <= 10": lambda g: g <= 10,
}
KEEP = ["listing_date", "company_name", "listing_year", "quarter", "y", "listing_gain_pct",
        "gmp_pct_of_issue", "log_total"]

def add_gmp_transform(d: pd.DataFrame) -> pd.DataFrame:
    """
    Add the deterministic asinh(GMP/10) feature.

    Does not modify the raw GMP feature or the input DataFrame.
    The transformation preserves zero, sign and ordering.
    """

    if "gmp_pct_of_issue" not in d.columns:
        raise ValueError(
            "Missing required column: gmp_pct_of_issue"
        )

    out = d.copy()

    gmp = pd.to_numeric(
        out["gmp_pct_of_issue"],
        errors="coerce"
    )

    finite_values = gmp.dropna().to_numpy(dtype=float)

    if not np.isfinite(finite_values).all():
        raise ValueError(
            "GMP contains infinite values. Clean the data before evaluation."
        )

    out["gmp_asinh10"] = np.arcsinh(
        gmp.astype(float) / 10.0
    )

    return out

# ---------------------------------------------------------------- data and folds
def load_eval_frame(path, min_year: int = 2020) -> pd.DataFrame:
    d = pd.read_csv(path, parse_dates=["listing_date"])
    d = d[(d["listing_year"] >= min_year) & d["gmp_pct_of_issue"].notna() & d["log_total"].notna()].copy()
    d = d.sort_values(["listing_date", "company_name", "issue_price"], kind="stable").reset_index(drop=True)
    d["y"] = (d["listing_gain_pct"] > 0).astype(int)

    d["quarter"] = (d["listing_date"].dt.to_period("Q").astype(str))
    d = add_gmp_transform(d)
    return d


def apply_labels(d: pd.DataFrame, variant: str = "strict") -> pd.DataFrame:
    if variant == "strict":
        return d.copy()
    if variant == "clear_only":
        return d[d["listing_gain_pct"].abs() > FLAT_BAND].reset_index(drop=True)
    raise ValueError(f"unknown label variant: {variant}")


def make_model():
    return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(max_iter=2000))


def walk_forward(
    d: pd.DataFrame,
    test_years=range(2022, 2027),
    min_train: int = 40
):
    """
    Expanding-window walk-forward validation.

    All SPECS use identical train/test rows, years and targets.
    Raw and transformed GMP use the same model factory.
    """

    d = add_gmp_transform(d)

    preds = []
    folds = []

    for yr in test_years:

        tr = d[
            d["listing_year"] < yr
        ]

        te = d[
            d["listing_year"] == yr
        ]

        if (
            len(tr) < min_train
            or te.empty
            or tr["y"].nunique() < 2
        ):
            continue

        out = te[KEEP].copy()

        out["p_prior"] = tr["y"].mean()

        for name, feats in SPECS.items():

            model = make_model()

            model.fit(
                tr[feats],
                tr["y"]
            )

            probabilities = model.predict_proba(
                te[feats]
            )[:, 1]

            out[f"p::{name}"] = probabilities

        preds.append(out)

        folds.append({

            "test_year": yr,

            "n_train": len(tr),

            "n_test": len(te),

            "train_max_date": tr["listing_date"].max(),

            "test_min_date": te["listing_date"].min(),

        })

    if not preds:

        raise ValueError(
            "No valid walk-forward folds were generated."
        )

    return (
        pd.concat(preds, ignore_index=True),
        pd.DataFrame(folds)
    )


# ---------------------------------------------------------------- metrics
def ece(y, p, bins: int = 10) -> float:
    """Expected calibration error with equal-frequency bins."""
    y, p = np.asarray(y, dtype=float), np.asarray(p, dtype=float)
    order = np.argsort(p, kind="stable")
    y, p = y[order], p[order]
    return float(sum(len(ix) / len(p) * abs(y[ix].mean() - p[ix].mean())
                     for ix in np.array_split(np.arange(len(p)), bins) if len(ix)))


def core_metrics(y, p) -> dict:
    y = np.asarray(y)
    p = np.clip(np.asarray(p, dtype=float), 1e-6, 1 - 1e-6)
    return {"auc": roc_auc_score(y, p), "pr_auc_neg": average_precision_score(1 - y, 1 - p),
            "brier": brier_score_loss(y, p), "logloss": log_loss(y, p), "ece": ece(y, p),
            "mean_p": float(p.mean()), "actual": float(y.mean())}


def flag_metrics(y, p, rate: float) -> dict:
    """Flag the lowest-P(positive) share of IPOs as 'expected non-positive'."""
    y, p = np.asarray(y), np.asarray(p)
    k = max(1, int(round(rate * len(p))))
    idx = np.argsort(p, kind="stable")[:k]
    neg = y == 0
    caught = int(neg[idx].sum())
    return {"flagged": k, "recall_neg": caught / max(int(neg.sum()), 1), "precision_neg": caught / k}


def precision_at_recall(y, p, recall: float = 0.8) -> dict:
    y, p = np.asarray(y), np.asarray(p)
    order = np.argsort(p, kind="stable")
    cum = np.cumsum(y[order] == 0)
    k = int(np.searchsorted(cum, recall * cum[-1])) + 1
    return {"flag_rate": k / len(p), "precision_neg": float(cum[k - 1] / k)}


def bootstrap_deltas(
    pred: pd.DataFrame,
    ref: str,
    other: str,
    n_boot: int = 1000,
    seed: int = 42,
    by: Optional[str] = None
) -> dict:
    """
    Paired bootstrap of other - reference.

    Supports whole-block resampling, e.g. quarter.

    Negative differences favour the candidate for:
        Brier, log-loss, ECE

    Positive differences favour the candidate for:
        AUC, non-positive PR-AUC
    """

    if n_boot < 1:
        raise ValueError("n_boot must be positive.")

    required = {"y", ref, other}

    if by is not None:
        required.add(by)

    missing = required - set(pred.columns)

    if missing:
        raise ValueError(
            f"Missing bootstrap columns: {sorted(missing)}"
        )

    if pred.empty:
        raise ValueError("Cannot bootstrap an empty DataFrame.")

    y = pred["y"].to_numpy(dtype=int)

    pr = pred[ref].to_numpy(dtype=float)

    po = pred[other].to_numpy(dtype=float)

    if np.unique(y).size < 2:
        raise ValueError(
            "Bootstrap evaluation requires both outcome classes."
        )

    metric_names = {
        "dAUC": "auc",
        "dPR_AUC_neg": "pr_auc_neg",
        "dBrier": "brier",
        "dLogloss": "logloss",
        "dECE": "ece",
    }

    # Calculate the observed full-sample differences.
    raw_ref = core_metrics(y, pr)
    raw_other = core_metrics(y, po)

    observed = {
        key: raw_other[metric] - raw_ref[metric]
        for key, metric in metric_names.items()
    }

    # Construct bootstrap blocks.
    if by is None:

        blocks = [
            np.array([i])
            for i in range(len(y))
        ]

    else:

        keys = pred[by].to_numpy()

        if pd.isna(keys).any():
            raise ValueError(
                f"Bootstrap grouping column {by!r} has missing values."
            )

        blocks = [
            np.flatnonzero(keys == group)
            for group in pd.unique(keys)
        ]

    if not blocks:
        raise ValueError("No bootstrap blocks available.")

    rng = np.random.default_rng(seed)

    samples = {
        name: []
        for name in metric_names
    }

    for _ in range(n_boot):

        selected_blocks = rng.integers(
            0,
            len(blocks),
            size=len(blocks)
        )

        indices = np.concatenate([
            blocks[i]
            for i in selected_blocks
        ])

        yy = y[indices]

        # AUC and average precision require both classes.
        if np.unique(yy).size < 2:
            continue

        ref_metrics = core_metrics(
            yy,
            pr[indices]
        )

        other_metrics = core_metrics(
            yy,
            po[indices]
        )

        for key, metric in metric_names.items():

            samples[key].append(
                other_metrics[metric]
                - ref_metrics[metric]
            )

    # Calculate confidence intervals.
    result = {}

    for name, values in samples.items():

        if not values:
            raise RuntimeError(
                f"No valid bootstrap replicates for {name}."
            )

        low, high = np.percentile(
            values,
            [2.5, 97.5]
        )

        result[name] = observed[name]

        result[f"{name}_lo"] = float(low)

        result[f"{name}_hi"] = float(high)

    result["reps"] = min(
        len(values)
        for values in samples.values()
    )

    result["requested_reps"] = n_boot

    return result


# ---------------------------------------------------------------- tables
def to_md(df: pd.DataFrame, digits: int = 3) -> str:
    def f(v):
        if isinstance(v, (float, np.floating)):
            return "" if np.isnan(v) else f"{v:.{digits}f}"
        return str(v)
    head = "| " + " | ".join(map(str, df.columns)) + " |"
    body = ["| " + " | ".join(f(v) for v in r) + " |" for r in df.itertuples(index=False)]
    return "\n".join([head, "|" + "---|" * len(df.columns)] + body)


def scoreboard(pred: pd.DataFrame) -> pd.DataFrame:
    y = pred["y"].to_numpy()
    entries = [("prior only (train rate)", pred["p_prior"].to_numpy())] + \
              [(m, pred[f"p::{m}"].to_numpy()) for m in SPECS]
    rows = []
    for name, p in entries:
        r = {"model": name, **core_metrics(y, p)}
        for rate in FLAG_RATES:
            r[f"recall@{int(rate * 100)}%flag"] = np.nan if name.startswith("prior") else flag_metrics(y, p, rate)["recall_neg"]
        pred_neg = p < 0.5
        r["flag_rate@0.5"] = float(pred_neg.mean())
        r["recall@0.5"] = float((pred_neg & (y == 0)).sum() / max(int((y == 0).sum()), 1))
        rows.append(r)
    return pd.DataFrame(rows)


def delta_table(pred: pd.DataFrame, by: Optional[str], n_boot: int) -> pd.DataFrame:
    ref = f"p::{REF}"
    return pd.DataFrame([{"model": m, **bootstrap_deltas(pred, ref, f"p::{m}", n_boot=n_boot, by=by)}
                         for m in SPECS if m != REF])


def zone_table(pred: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for z, f in ZONES.items():
        s = pred[f(pred["gmp_pct_of_issue"])]
        if s["y"].nunique() < 2:
            continue
        r = {"zone": z, "n": len(s), "negatives": int((s["y"] == 0).sum())}
        for m in SPECS:
            r[f"AUC {m.split()[0]}"] = roc_auc_score(s["y"], s[f"p::{m}"])
        r["Brier A"] = brier_score_loss(s["y"], s[f"p::{REF}"])
        rows.append(r)
    return pd.DataFrame(rows)


def by_year(pred: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for yr, g in pred.groupby("listing_year"):
        r = {"year": int(yr), "n": len(g), "negatives": int((g["y"] == 0).sum())}
        if g["y"].nunique() > 1:
            for m in SPECS:
                r[m.split()[0]] = roc_auc_score(g["y"], g[f"p::{m}"])
        rows.append(r)
    return pd.DataFrame(rows)


def rule_baselines(pred: pd.DataFrame) -> pd.DataFrame:
    y, g = pred["y"].to_numpy(), pred["gmp_pct_of_issue"].to_numpy()
    neg = y == 0
    rows = [{"rule": "majority class (never flag)", "flagged": 0, "flag_rate": 0.0,
             "recall_neg": 0.0, "precision_neg": np.nan}]
    for t in (0, 5, 10):
        flag = g <= t
        caught = int((flag & neg).sum())
        rows.append({"rule": f"flag if GMP <= {t}%", "flagged": int(flag.sum()), "flag_rate": float(flag.mean()),
                     "recall_neg": caught / max(int(neg.sum()), 1), "precision_neg": caught / max(int(flag.sum()), 1)})
    return pd.DataFrame(rows)


def reliability_plot(pred: pd.DataFrame, models: List[str], path, bins: int = 10) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(5.5, 5.5))
    ax.plot([0, 1], [0, 1], "k--", lw=1)
    y = pred["y"].to_numpy()
    for m in models:
        p = pred[f"p::{m}"].to_numpy()
        parts = np.array_split(np.argsort(p, kind="stable"), bins)
        ax.plot([p[ix].mean() for ix in parts], [y[ix].mean() for ix in parts], marker="o", label=m)
    ax.set(xlabel="mean predicted P(positive)", ylabel="actual positive rate",
           title="Reliability (equal-frequency bins)")
    ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(path, dpi=120); plt.close(fig)


def build_report(pred: pd.DataFrame, folds: pd.DataFrame, label: str, n_boot: int = 1000) -> str:
    y = pred["y"].to_numpy()
    folds_md = folds.assign(train_max_date=folds["train_max_date"].dt.strftime("%Y-%m-%d"),
                            test_min_date=folds["test_min_date"].dt.strftime("%Y-%m-%d"))
    return "\n".join([
        f"## Label variant: {label}", "",
        f"Test rows {len(pred)} | positive {int(y.sum())} ({y.mean():.1%}) | non-positive {int((y == 0).sum())} "
        f"| majority-class accuracy {max(y.mean(), 1 - y.mean()):.3f}", "",
        "### Folds", to_md(folds_md), "",
        "### Scoreboard (probability quality; recall of non-positives at fixed flag rates)", to_md(scoreboard(pred)), "",
        "### Paired differences vs A (95% bootstrap intervals; negative dBrier = better than A)",
        "Row bootstrap:", to_md(delta_table(pred, None, n_boot)), "",
        "Quarter-block bootstrap:", to_md(delta_table(pred, "quarter", n_boot)), "",
        "### By GMP zone", to_md(zone_table(pred)), "",
        "### AUC by test year", to_md(by_year(pred)), "",
        "### Simple rules to beat (at their own flag rates)", to_md(rule_baselines(pred)), ""])


def run_all(base_path, out_dir, fig_dir, labels=("strict", "clear_only"), n_boot: int = 1000) -> str:
    out_dir, fig_dir = Path(out_dir), Path(fig_dir)
    out_dir.mkdir(parents=True, exist_ok=True); fig_dir.mkdir(parents=True, exist_ok=True)
    base = load_eval_frame(base_path)
    parts = ["# IPOVision scoreboard (auto-generated)", "",
             f"Source `{Path(base_path).name}` | rows with GMP and total subscription, 2020 onward: {len(base)} | "
             "expanding walk-forward, test years 2022-2026 | unweighted logistic regression (L2, C=1)", ""]
    for label in labels:
        pred, folds = walk_forward(apply_labels(base, label))
        pred.to_csv(out_dir / f"predictions_v3_{label}.csv", index=False)
        reliability_plot(
    pred,
    [
        REF,
        ASINH_MODEL
    ],fig_dir / f"09_reliability_{label}.png")
        parts.append(build_report(pred, folds, label, n_boot))
    text = "\n".join(parts)
    (out_dir / "scoreboard_v3.md").write_text(text, encoding="utf-8")
    return text