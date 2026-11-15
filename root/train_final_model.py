import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.evaluation.harness import REF, load_eval_frame, to_md, walk_forward
from src.models.final_model import BAND_NAMES, band_labels, interval_coverage, predict, save_bundle, train

BASE = ROOT / "data/interim/kaggle/model_base_v3.csv"
MODEL_PATH, REPORT = ROOT / "src/models/artifacts/ipovision_final.joblib", ROOT / "reports/evaluation/final_model_report.md"

base = pd.read_csv(BASE, parse_dates=["listing_date"])
bundle = train(base)
save_bundle(bundle, MODEL_PATH)

# 1) do the risk bands mean something? (out-of-sample, walk-forward predictions of model A)
frame = load_eval_frame(BASE)
pred, _ = walk_forward(frame)
pred["p_non"] = 1 - pred[f"p::{REF}"]
pred["band"] = band_labels(pred["p_non"].to_numpy())
pred["non_positive"] = 1 - pred["y"]
bands = (pred.groupby("band").agg(ipos=("y", "size"), predicted_non_positive=("p_non", "mean"),
                                  actual_non_positive=("non_positive", "mean"))
         .reindex(list(BAND_NAMES)).reset_index())

# 2) does the 80% gain interval cover about 80%? (intervals built only from earlier years)
cov = interval_coverage(frame, range(2023, 2027))
cov_all = pd.DataFrame([{"scope": "all", "n": len(cov), "coverage": cov["covered"].mean(), "mean_width_pts": cov["width"].mean()}])
cov_by = (cov.groupby("bucket").agg(n=("covered", "size"), coverage=("covered", "mean"), mean_width_pts=("width", "mean"))
          .reset_index())

# 3) worked examples
rows = []
for label, kw in [("GMP -5%", dict(gmp_pct=-5, issue_price=100)), ("GMP 0%", dict(gmp_pct=0, issue_price=100)),
                  ("GMP 5%", dict(gmp_pct=5, issue_price=100)), ("GMP 15%", dict(gmp_pct=15, issue_price=100)),
                  ("GMP 40%", dict(gmp_pct=40, issue_price=100)), ("No GMP, 3x subscription", dict(total_sub=3)),
                  ("No GMP, 80x subscription", dict(total_sub=80)), ("No inputs", {})]:
    r = predict(bundle, **kw)
    lo, hi = r["gain_interval_pct"] or (float("nan"), float("nan"))
    rows.append({"input": label, "model": r["model_used"], "P(positive)": r["p_positive"],
                 "P(non-positive)": r["p_non_positive"], "band": r["band"], "gain 80% low": lo, "gain 80% high": hi})
examples = pd.DataFrame(rows)

text = "\n".join([
    "# IPOVision final model report (auto-generated)", "",
    f"Model: GMP-only logistic regression (benchmark A), subscription-only fallback. Trained on {bundle['n_gmp_rows']} IPOs with a GMP "
    f"and {bundle['n_sub_rows']} with subscription ({bundle['listing_dates'][0]} to {bundle['listing_dates'][1]}). "
    f"Saved to `{MODEL_PATH.relative_to(ROOT)}`.", "",
    "## Do the risk bands mean something? (out-of-sample, walk-forward 2022-2026)", to_md(bands), "",
    "## 80% gain interval coverage (built from earlier years only, test 2023-2026)", to_md(cov_all), "", to_md(cov_by), "",
    "## Worked examples (issue price 100 where a price is shown)", to_md(examples), "",
    "## Residual quantiles used for the interval (actual gain minus GMP%)",
    to_md(pd.DataFrame([{"bucket": k, **(v or {})} for k, v in bundle["residual_quantiles"].items()])), ""])
REPORT.write_text(text, encoding="utf-8")
print(text)