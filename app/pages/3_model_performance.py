import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.components.common import (
    BASE_PATH,
    apply_candy_theme,
    candy_plotly_layout,
    footer,
    page_header,
)

st.set_page_config(page_title="Model performance - IPOVision", page_icon="📈", layout="wide")
apply_candy_theme()

page_header(
    title="Model performance",
    subtitle=(
        "Every metric evaluated via walk-forward validation: each test year is predicted strictly "
        "using models trained on prior cohorts, evaluated on identical test rows."
    ),
    badge="Walk-Forward Validation",
    category="Benchmark Suite v2.4",
    live_text="Held-out validation 2022–2026",
    dot_color="blue",
)


@st.cache_data(show_spinner="Running the walk-forward evaluation...")
def run_eval():
    from src.evaluation.harness import (
        REF,
        by_year,
        load_eval_frame,
        rule_baselines,
        scoreboard,
        walk_forward,
        zone_table,
    )
    from src.models.final_model import band_labels, interval_coverage

    frame = load_eval_frame(BASE_PATH)
    pred, _ = walk_forward(frame)
    pred["p_non"] = 1 - pred[f"p::{REF}"]
    pred["band"] = band_labels(pred["p_non"].to_numpy())
    pred["non_positive"] = 1 - pred["y"]
    bands = (
        pred.groupby("band")
        .agg(
            IPOs=("y", "size"),
            predicted=("p_non", "mean"),
            actual=("non_positive", "mean"),
        )
        .reindex(["Low", "Medium", "High"])
        .reset_index()
    )
    cov = interval_coverage(frame, range(2023, 2027))
    return pred, scoreboard(pred), zone_table(pred), by_year(pred), rule_baselines(pred), bands, cov


pred, board, zones, years, rules, bands, cov = run_eval()
a = board[board["model"] == "A GMP only"].iloc[0]

with st.container():
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Test IPOs", f"{len(pred):,}")
    c2.metric("AUC (GMP model)", f"{a['auc']:.3f}")
    c3.metric(
        "Brier score",
        f"{a['brier']:.3f}",
        help="Lower is better. Always predicting the base rate scores about 0.195.",
    )
    c4.metric("Caught at 35% flagged", f"{a['recall@35%flag']:.0%}")

st.write("")

st.subheader("All models, same rows")
cols = ["model", "auc", "brier", "logloss", "ece", "recall@20%flag", "recall@35%flag", "recall@50%flag"]
st.dataframe(board[cols].round(3), hide_index=True, width="stretch")
st.caption(
    "The GMP-only model is the benchmark. Adding subscription, size, market and momentum features did not improve "
    "the Brier score, and a gradient-boosting and a random-forest challenger did not beat it either."
)

left, right = st.columns(2, gap="medium")
with left:
    st.subheader("Do the risk bands mean something?")
    st.dataframe(bands.round(3), hide_index=True, width="stretch")
    st.caption("Actual share of IPOs that listed flat or lower within each band, out-of-sample.")

    st.subheader("80% gain-range coverage")
    st.info(
        f"**{cov['covered'].mean():.1%}** of {len(cov)} held-out IPOs fell inside the 80% range "
        f"(mean width {cov['width'].mean():.0f} points)."
    )

with right:
    st.subheader("Calibration curve")
    p, y = pred["p::A GMP only"].to_numpy(), pred["y"].to_numpy()
    parts = np.array_split(np.argsort(p, kind="stable"), 10)
    rel = pd.DataFrame({"predicted": [p[i].mean() for i in parts], "actual": [y[i].mean() for i in parts]})

    fig = go.Figure()
    fig.add_scatter(
        x=[0, 1],
        y=[0, 1],
        mode="lines",
        line=dict(dash="dash", color="#7c52aa", width=1.5),
        name="Perfect calibration",
    )
    fig.add_scatter(
        x=rel["predicted"],
        y=rel["actual"],
        mode="lines+markers",
        line=dict(color="#e040a0", width=2.5),
        marker=dict(size=8, color="#e040a0"),
        name="GMP model",
    )
    candy_plotly_layout(fig, title="Reliability diagram (predicted vs actual)", height=340)
    fig.update_layout(xaxis_title="Predicted P(positive)", yaxis_title="Actual positive rate")
    st.plotly_chart(fig, width="stretch")

st.subheader("Where the model is weak: GMP zones")
st.dataframe(zones.round(3), hide_index=True, width="stretch")
st.caption(
    "Inside the 0 to 10% GMP zone about half of IPOs list flat or lower, and every model is close to a coin flip there."
)

col_a, col_b = st.columns(2, gap="medium")
with col_a:
    st.subheader("By year (AUC)")
    st.dataframe(years.round(3), hide_index=True, width="stretch")
with col_b:
    st.subheader("Simple rules the model must beat")
    st.dataframe(rules.round(3), hide_index=True, width="stretch")

footer()
