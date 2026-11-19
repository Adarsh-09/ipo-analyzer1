import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import streamlit as st

from app.components.common import apply_candy_theme, footer, page_header

st.set_page_config(page_title="About - IPOVision", page_icon="📈", layout="wide")
apply_candy_theme()

page_header(
    title="About and limitations",
    subtitle=(
        "Clear, transparent documentation on historical data sourcing, model architecture, "
        "walk-forward validation, and known empirical boundaries across Indian mainboard listings."
    ),
    badge="Methodology & Data Governance",
    category="Terminal Note v1.4.2",
    live_text="Grounded research documentation",
    dot_color="green",
)

c1, c2, c3 = st.columns(3, gap="medium")

with c1:
    with st.container():
        st.markdown(
            """
            <div style="display: inline-block; padding: 4px 10px; background: #ffd6ee; border-radius: 9999px; font-size: 11px; font-weight: 700; color: #a02070; margin-bottom: 8px;">SCOPE</div>
            <h3 style="margin-top: 0; font-size: 1.15rem; color: #2e1a28;">What this is</h3>
            <p style="font-size: 0.9rem; color: #604868; line-height: 1.6;">
            A research project that estimates the empirical probability an Indian mainboard initial public offering (IPO)
            lists above its issue price on debut day, using the final grey-market premium (GMP) quoted the day before listing,
            with subscription demand as a fallback.
            </p>
            """,
            unsafe_allow_html=True,
        )

with c2:
    with st.container():
        st.markdown(
            """
            <div style="display: inline-block; padding: 4px 10px; background: #eedcff; border-radius: 9999px; font-size: 11px; font-weight: 700; color: #4a3068; margin-bottom: 8px;">PROVENANCE</div>
            <h3 style="margin-top: 0; font-size: 1.15rem; color: #2e1a28;">Data & Sourcing</h3>
            <p style="font-size: 0.9rem; color: #604868; line-height: 1.6;">
            Listing and subscription history spans 2017 to 2026 from Kaggle, cross-checked and extended with InvestorGain's GMP
            performance tracker. REITs, InvITs, and follow-on offers are excluded. Every sourced value is stored with full provenance.
            </p>
            """,
            unsafe_allow_html=True,
        )

with c3:
    with st.container():
        st.markdown(
            """
            <div style="display: inline-block; padding: 4px 10px; background: #c8eaff; border-radius: 9999px; font-size: 11px; font-weight: 700; color: #005580; margin-bottom: 8px;">BENCHMARK</div>
            <h3 style="margin-top: 0; font-size: 1.15rem; color: #2e1a28;">Method & Testing</h3>
            <p style="font-size: 0.9rem; color: #604868; line-height: 1.6;">
            Logistic regression on GMP validated via walk-forward testing across 2022 to 2026. Richer feature sets, gradient
            boosting, and random forests were rigorously benchmarked and did not beat the calibrated GMP-only benchmark.
            </p>
            """,
            unsafe_allow_html=True,
        )

st.write("")
st.subheader("Limits to keep in mind")

with st.container():
    st.markdown(
        """
        - **Listing-eve timing:** The GMP is a single final quote with no intraday timestamp, so this is a listing-eve model, not a pre-issue one.
        - **Unofficial sentiment:** GMP quotes originate from informal grey-market broker networks; aggregator sources occasionally disagree.
        - **The 0% to 10% coin flip:** When GMP is at or below 10%, historical outcomes have hovered near 50%; the model's certainty is weak in this regime.
        - **Exchange tick discrepancies:** About 15% of IPOs open within ±2% of issue price; classification can depend on whether NSE or BSE opening tick is referenced.
        - **Pre-2020 subscription verification:** Subscription breakdowns for rows prior to late 2020 could not be independently cross-verified against primary exchange PDFs.
        - **Fundamental features:** The statistical model relies on pricing and sentiment signals; fundamental metrics require the RAG Prospectus Workbench.
        """
    )

footer()
