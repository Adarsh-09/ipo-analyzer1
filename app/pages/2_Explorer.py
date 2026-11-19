import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import plotly.express as px
import streamlit as st

from app.components.common import (
    apply_candy_theme,
    candy_plotly_layout,
    footer,
    load_ipos,
    page_header,
)

st.set_page_config(page_title="Explorer - IPOVision", page_icon="📈", layout="wide")
apply_candy_theme()

page_header(
    title="IPO explorer",
    subtitle=(
        "Explore historical IPO debut performances, filter by subscription tiers and GMP sentiment, "
        "and inspect raw cohort data."
    ),
    badge="Cohort Analysis",
    category="Historical Data Engine",
    live_text="Interactive dataset filters",
    dot_color="purple",
)

d = load_ipos()

with st.sidebar:
    st.markdown("### 🔍 Filters")
    ylo, yhi = int(d["year"].min()), int(d["year"].max())
    years = st.slider("Listing year", ylo, yhi, (ylo, yhi))
    outcome = st.multiselect(
        "Outcome",
        ["Positive", "Flat or lower"],
        default=["Positive", "Flat or lower"],
    )
    need_gmp = st.checkbox("Only IPOs with a GMP", value=False)
    smax = float(min(500.0, d["overall_subscription"].max()))
    sub_range = st.slider("Total subscription (x)", 0.0, smax, (0.0, smax))
    q = st.text_input("Company name contains", placeholder="e.g. Tata, Zomato")

f = d[d["year"].between(*years) & d["outcome"].isin(outcome)]
if need_gmp:
    f = f[f["gmp_pct"].notna()]
f = f[f["overall_subscription"].fillna(0).between(*sub_range)]
if q:
    f = f[f["company_name"].str.contains(q, case=False, na=False)]

with st.container():
    a, b, c = st.columns(3)
    a.metric("IPOs shown", f"{len(f):,}")
    b.metric("Positive rate", f"{f['listing_positive'].mean():.1%}" if len(f) else "n/a")
    c.metric("Median gain", f"{f['listing_gain_pct'].median():.1f}%" if len(f) else "n/a")

st.write("")

s = f.dropna(subset=["gmp_pct"])
if not s.empty:
    with st.container():
        fig = px.scatter(
            s.assign(gain=s["listing_gain_pct"].clip(-60, 300)),
            x="gmp_pct",
            y="gain",
            color="outcome",
            hover_name="company_name",
            hover_data=["listing_date", "overall_subscription"],
            labels={"gmp_pct": "Final GMP, % of issue price", "gain": "Listing gain % (clipped)"},
            color_discrete_map={"Positive": "#16a34a", "Flat or lower": "#e53e3e"},
        )
        lim = [float(s["gmp_pct"].min()), float(s["gmp_pct"].max())]
        if lim[0] < lim[1]:
            fig.add_shape(
                type="line",
                x0=lim[0],
                y0=lim[0],
                x1=lim[1],
                y1=lim[1],
                line=dict(dash="dash", color="#7c52aa", width=1.5),
            )
        candy_plotly_layout(fig, title="Final GMP vs actual listing gain", height=420)
        st.plotly_chart(fig, width="stretch")

st.subheader("Cohort listings")
if f.empty:
    st.info("No historical IPOs match the selected filter criteria. Try expanding the listing year range or clearing search filters in the sidebar.")
else:
    view = (
        f[
            [
                "company_name",
                "listing_date",
                "issue_price",
                "issue_size_cr",
                "overall_subscription",
                "gmp",
                "gmp_pct",
                "listing_open_price",
                "listing_gain_pct",
                "outcome",
            ]
        ]
        .sort_values("listing_date", ascending=False)
        .round(2)
    )
    view["listing_date"] = view["listing_date"].dt.strftime("%Y-%m-%d")

    st.dataframe(view, hide_index=True, width="stretch")

    st.download_button(
        label="Export filtered cohort (CSV)",
        data=view.to_csv(index=False).encode("utf-8"),
        file_name="ipovision_filtered.csv",
        mime="text/csv",
        icon=":material/download:",
        width="stretch",
    )

footer()
