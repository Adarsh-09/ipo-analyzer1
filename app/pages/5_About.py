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
    st.markdown(
        """
        <div class="candy-card" style="height: 100%;">
          <div style="display: inline-block; padding: 4px 10px; background: #ffd6ee; border-radius: 9999px; font-size: 11px; font-weight: 700; color: #a02070; margin-bottom: 8px;">SCOPE</div>
          <h3 style="margin-top: 0; font-size: 1.15rem; color: #2e1a28;">What this is</h3>
          <p style="font-size: 0.9rem; color: #604868; line-height: 1.6; margin-bottom: 0;">
          A research project that estimates the empirical probability an Indian mainboard initial public offering (IPO)
          lists above its issue price on debut day, using the final grey-market premium (GMP) quoted the day before listing,
          with subscription demand as a fallback.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c2:
    st.markdown(
        """
        <div class="candy-card" style="height: 100%;">
          <div style="display: inline-block; padding: 4px 10px; background: #eedcff; border-radius: 9999px; font-size: 11px; font-weight: 700; color: #4a3068; margin-bottom: 8px;">PROVENANCE</div>
          <h3 style="margin-top: 0; font-size: 1.15rem; color: #2e1a28;">Data & Sourcing</h3>
          <p style="font-size: 0.9rem; color: #604868; line-height: 1.6; margin-bottom: 0;">
          Listing and subscription history spans 2017 to 2026 from Kaggle, cross-checked and extended with InvestorGain's GMP
          performance tracker. REITs, InvITs, and follow-on offers are excluded. Every sourced value is stored with full provenance.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c3:
    st.markdown(
        """
        <div class="candy-card" style="height: 100%;">
          <div style="display: inline-block; padding: 4px 10px; background: #c8eaff; border-radius: 9999px; font-size: 11px; font-weight: 700; color: #005580; margin-bottom: 8px;">BENCHMARK</div>
          <h3 style="margin-top: 0; font-size: 1.15rem; color: #2e1a28;">Method & Testing</h3>
          <p style="font-size: 0.9rem; color: #604868; line-height: 1.6; margin-bottom: 0;">
          Logistic regression on GMP validated via walk-forward testing across 2022 to 2026. Richer feature sets, gradient
          boosting, and random forests were rigorously benchmarked and did not beat the calibrated GMP-only benchmark.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.write("")
st.subheader("Limits to keep in mind")

st.markdown(
    """
    <div class="candy-card" style="border-left: 4px solid #7c52aa;">
      <ul style="margin: 0; padding-left: 1.2rem; color: #4a3068; line-height: 1.7; font-size: 0.92rem;">
        <li><strong>Listing-eve timing:</strong> The GMP is a single final quote with no intraday timestamp, so this is a listing-eve model, not a pre-issue one.</li>
        <li><strong>Unofficial sentiment:</strong> GMP quotes originate from informal grey-market broker networks; aggregator sources occasionally disagree.</li>
        <li><strong>The 0% to 10% coin flip:</strong> When GMP is at or below 10%, historical outcomes have hovered near 50%; the model's certainty is weak in this regime.</li>
        <li><strong>Exchange tick discrepancies:</strong> About 15% of IPOs open within ±2% of issue price; classification can depend on whether NSE or BSE opening tick is referenced.</li>
        <li><strong>Pre-2020 subscription verification:</strong> Subscription breakdowns for rows prior to late 2020 could not be independently cross-verified against primary exchange PDFs.</li>
        <li><strong>Fundamental features:</strong> The statistical model relies on pricing and sentiment signals; fundamental metrics require the RAG Prospectus Workbench.</li>
      </ul>
    </div>
    """,
    unsafe_allow_html=True,
)

footer()
