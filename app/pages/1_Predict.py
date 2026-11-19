import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import streamlit as st

from app.components.common import (
    apply_candy_theme,
    bucket_stats,
    footer,
    load_ipos,
    page_header,
    require_model,
)
from src.models.final_model import BAND_EDGES, bucket_name, predict

st.set_page_config(page_title="Predict - IPOVision", page_icon="📈", layout="wide")
apply_candy_theme()

page_header(
    title="Predict a listing",
    subtitle=(
        "Estimate the empirical probability and expected listing-day gain based on baseline issue price, "
        "unofficial grey-market premium (GMP), and institutional demand bands."
    ),
    badge="Predictive Engine",
    category="Logistic Model (Walk-Forward Validated v2.1)",
    live_text="Feed updated · NSE & BSE Grey Market",
    dot_color="green",
)

bundle, d = require_model(), load_ipos()

left, right = st.columns([1, 1.35], gap="large")

with left:
    with st.container():
        st.subheader("Parameters")
        issue_price = st.number_input("Issue price (₹)", min_value=1.0, value=100.0, step=1.0)
        has_gmp = st.checkbox("I have a current GMP", value=True)
        gmp_pct = None
        if has_gmp:
            if hasattr(st, "segmented_control"):
                mode = st.segmented_control(
                    "GMP entered as",
                    ["₹ per share", "% of issue price"],
                    default="₹ per share",
                    key="gmp_mode_select",
                ) or "₹ per share"
            else:
                mode = st.radio("GMP entered as", ["₹ per share", "% of issue price"], horizontal=True)
            gmp_val = st.number_input("GMP", value=10.0, step=1.0)
            gmp_pct = gmp_val / issue_price * 100 if mode == "₹ per share" else gmp_val
            st.caption(f"= **{gmp_pct:.1f}%** of the issue price")

        has_sub = st.checkbox("I know the total subscription", value=False)
        total_sub = (
            st.number_input("Total subscription (times)", min_value=0.01, value=10.0, step=1.0)
            if has_sub
            else None
        )
        if has_gmp and has_sub:
            st.info(
                "With a GMP the model uses the GMP only. Adding subscription did not improve held-out accuracy."
            )

res = predict(bundle, gmp_pct=gmp_pct, total_sub=total_sub, issue_price=issue_price)

with right:
    with st.container():
        st.subheader("Model estimation")
        m1, m2, m3 = st.columns(3)
        m1.metric("Lists above issue price", f"{res['p_positive']:.0%}")
        m2.metric("Flat or lower", f"{res['p_non_positive']:.0%}")
        m3.metric("Risk band", res["band"])

        low, high = BAND_EDGES
        band_messages = {
            "Low": f"Low risk: under {low:.0%} chance of a flat or lower listing.",
            "Medium": f"Medium risk: {low:.0%} to {high:.0%} chance of a flat or lower listing.",
            "High": f"High risk: {high:.0%} or more chance of a flat or lower listing.",
        }
        band_fn = {"Low": st.success, "Medium": st.warning, "High": st.error}[res["band"]]
        band_fn(band_messages[res["band"]])

        st.progress(float(res["p_positive"]), text="Empirical listing probability")

        if res["gain_interval_pct"]:
            lo, hi = res["gain_interval_pct"]
            implied_row = (
                f"<div style='display: flex; justify-content: space-between; align-items: baseline;'>"
                f"<span style='font-size: 12px; font-weight: 600; text-transform: uppercase; color: #7c52aa;'>Implied Debut Price</span>"
                f"<span style='font-size: 15px; font-weight: 700; color: #e040a0;'>₹{res['implied_listing_price']:.2f} "
                f"<span style='font-size: 12px; font-weight: 500; color: #907898;'>(80% range ₹{res['price_interval'][0]:.2f} - ₹{res['price_interval'][1]:.2f})</span></span></div>"
                if res.get("price_interval")
                else ""
            )
            card_html = f"""
            <div style="background: #ffffff; border: 1px solid #ece2ec; border-radius: 14px; padding: 14px 18px; margin: 12px 0; box-shadow: 0 2px 8px rgba(124, 82, 170, 0.05);">
              <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 6px;">
                <span style="font-size: 12px; font-weight: 600; text-transform: uppercase; color: #7c52aa;">80% Listing Gain Range</span>
                <span style="font-size: 16px; font-weight: 700; color: #2e1a28;">{lo:+.0f}% to {hi:+.0f}%</span>
              </div>
              {implied_row}
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)

        for note in res["notes"]:
            st.warning(note)

        st.caption(f"Model used: `{res['model_used']}`")

if gmp_pct is not None:
    st.write("")
    st.subheader("Similar past IPOs")
    name = bucket_name(gmp_pct)
    row = bucket_stats(d).query("`GMP bucket` == @name")
    if not row.empty:
        r = row.iloc[0]
        st.markdown(
            f"IPOs with a final GMP in the same range (**{name}**): **{int(r['IPOs'])}**, "
            f"**{r['positive_rate']:.0%}** listed positive, median gain **{r['median_gain']:.1f}%**, "
            f"middle 80% of outcomes **{r['gain_p10']:.0f}%** to **{r['gain_p90']:.0f}%**."
        )

    near = (
        d.dropna(subset=["gmp_pct"])
        .assign(diff=lambda x: (x["gmp_pct"] - gmp_pct).abs())
        .nsmallest(8, "diff")
    )
    view = (
        near[
            [
                "company_name",
                "listing_date",
                "gmp_pct",
                "overall_subscription",
                "listing_gain_pct",
                "outcome",
            ]
        ]
        .rename(
            columns={
                "company_name": "Company",
                "listing_date": "Listing date",
                "gmp_pct": "GMP %",
                "overall_subscription": "Total sub (x)",
                "listing_gain_pct": "Actual gain %",
                "outcome": "Outcome",
            }
        )
        .round(1)
    )
    st.dataframe(view, hide_index=True, width="stretch")
elif total_sub is not None:
    st.write("")
    st.subheader("Similar subscription cohorts")
    st.caption("Historical IPOs with similar demand multiples:")
    near_sub = (
        d.dropna(subset=["overall_subscription"])
        .assign(diff=lambda x: (x["overall_subscription"] - total_sub).abs())
        .nsmallest(8, "diff")
    )
    view_sub = (
        near_sub[
            [
                "company_name",
                "listing_date",
                "issue_price",
                "overall_subscription",
                "listing_gain_pct",
                "outcome",
            ]
        ]
        .rename(
            columns={
                "company_name": "Company",
                "listing_date": "Listing date",
                "issue_price": "Issue price (₹)",
                "overall_subscription": "Total sub (x)",
                "listing_gain_pct": "Actual gain %",
                "outcome": "Outcome",
            }
        )
        .round(1)
    )
    st.dataframe(view_sub, hide_index=True, width="stretch")
else:
    st.write("")
    st.info("💡 Provide a GMP or subscription figure above to view matching historical IPO cohorts.")

footer()
