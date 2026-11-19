import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import plotly.express as px
import streamlit as st

from app.components.common import (
    apply_candy_theme,
    bucket_stats,
    candy_plotly_layout,
    footer,
    load_ipos,
    load_model,
    page_header,
)

st.set_page_config(page_title="IPOVision", page_icon="📈", layout="wide")
apply_candy_theme()
d = load_ipos()

page_header(
    title="IPOVision",
    subtitle=(
        "How likely is an Indian mainboard IPO to list above its issue price, and by roughly how much? "
        "Built on listing history, subscription data and the grey-market premium (GMP)."
    ),
    badge="Research Memo",
    category="Mainboard IPO Dataset",
    live_text=f"Verified sample · n={len(d):,}",
    dot_color="pink",
)

with st.container():
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("IPOs analysed", f"{len(d):,}")
    c2.metric("Listed positive", f"{d['listing_positive'].mean():.1%}")
    c3.metric("Median listing gain", f"{d['listing_gain_pct'].median():.1f}%")
    c4.metric("With a final GMP", f"{int(d['gmp'].notna().sum()):,}")
    c5.metric("Period", f"{d['listing_date'].min():%b %Y} to {d['listing_date'].max():%b %Y}")

st.write("")

left, right = st.columns(2)
with left:
    with st.container():
        yr = (
            d.groupby("year")
            .agg(
                IPOs=("ipo_id", "size"),
                positive_rate=("listing_positive", "mean"),
                median_gain=("listing_gain_pct", "median"),
            )
            .reset_index()
        )
        fig = px.bar(
            yr,
            x="year",
            y="positive_rate",
            text="IPOs",
            hover_data=["median_gain"],
            labels={"positive_rate": "Share listing positive", "year": "Listing year"},
            color_discrete_sequence=["#e040a0"],
        )
        fig.update_yaxes(tickformat=".0%", range=[0, 1])
        candy_plotly_layout(fig, title="Positive-listing rate by year (labels = IPOs)", height=380)
        st.plotly_chart(fig, width="stretch")

with right:
    with st.container():
        gain_df = d.assign(gain=d["listing_gain_pct"].clip(-60, 150))
        fig = px.histogram(
            gain_df,
            x="gain",
            color="outcome",
            nbins=60,
            labels={"gain": "Listing gain %"},
            color_discrete_map={"Positive": "#16a34a", "Flat or lower": "#e53e3e"},
        )
        candy_plotly_layout(
            fig,
            title="Listing gain distribution (clipped to -60% / +150% for display)",
            height=380,
        )
        st.plotly_chart(fig, width="stretch")

st.subheader("What the history says")
st.markdown(
    "The final GMP is the strongest single signal. Outcomes are nearly settled when GMP is high, "
    "and close to a coin flip when it is at or below 10%."
)
st.dataframe(bucket_stats(d), hide_index=True, width="stretch")

bundle = load_model()
if bundle:
    st.info(
        f"**Model architecture:** GMP-only logistic regression (subscription fallback), "
        f"trained on {bundle['n_gmp_rows']} IPOs with a GMP and {bundle['n_sub_rows']} with subscription data. "
        "Use the pages in the sidebar to predict, explore and review model performance."
    )

footer()
