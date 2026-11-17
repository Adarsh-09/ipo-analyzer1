import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import streamlit as st

from app.components.common import footer

st.set_page_config(page_title="About - IPOVision", page_icon="📈", layout="wide")
st.title("About and limitations")
st.markdown("""
**What this is.** A research project that estimates the chance an Indian mainboard IPO lists above its issue price,
using the final grey-market premium (GMP) quoted the day before listing, with subscription as a weaker fallback.

**Data.** Listing and subscription history from a public Kaggle IPO dataset (2017 to 2026), cross-checked and extended with
InvestorGain's GMP performance tracker. REITs, InvITs and follow-on offers are excluded. Every sourced value is stored with
its provenance and marked `unverified`.

**Method.** Logistic regression on GMP (benchmark and final model), validated by walk-forward testing on 2022 to 2026.
Richer feature sets, gradient boosting and random forests were tested and did not beat it.

**Limits to keep in mind**
- The GMP is a single final value with no timestamp, so this is a listing-eve model, not a pre-issue one.
- GMP is unofficial and sources disagree.
- When GMP is at or below 10%, outcomes have been close to a coin flip; the probability is weak evidence there.
- About 15% of IPOs list within 2% of their issue price, where the label depends on which exchange's open is used.
- Subscription values for rows before late 2020 could not be cross-checked.
- No financial, valuation or anchor-investor features are used yet.
""")
footer()