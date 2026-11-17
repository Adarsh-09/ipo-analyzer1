import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import streamlit as st

from app.components.common import bucket_stats, footer, load_ipos, require_model
from src.models.final_model import BAND_EDGES, bucket_name, predict

st.set_page_config(page_title="Predict - IPOVision", page_icon="📈", layout="wide")
st.title("Predict a listing")
bundle, d = require_model(), load_ipos()

left, right = st.columns([1, 1.4])
with left:
    issue_price = st.number_input("Issue price (₹)", min_value=1.0, value=100.0, step=1.0)
    has_gmp = st.checkbox("I have a current GMP", value=True)
    gmp_pct = None
    if has_gmp:
        mode = st.radio("GMP entered as", ["₹ per share", "% of issue price"], horizontal=True)
        gmp_val = st.number_input("GMP", value=10.0, step=1.0)
        gmp_pct = gmp_val / issue_price * 100 if mode == "₹ per share" else gmp_val
        st.caption(f"= {gmp_pct:.1f}% of the issue price")
    has_sub = st.checkbox("I know the total subscription", value=False)
    total_sub = st.number_input("Total subscription (times)", min_value=0.01, value=10.0, step=1.0) if has_sub else None
    if has_gmp and has_sub:
        st.info("With a GMP the model uses the GMP only. Adding subscription did not improve held-out accuracy.")

res = predict(bundle, gmp_pct=gmp_pct, total_sub=total_sub, issue_price=issue_price)
with right:
    m1, m2, m3 = st.columns(3)
    m1.metric("Lists above issue price", f"{res['p_positive']:.0%}")
    m2.metric("Flat or lower", f"{res['p_non_positive']:.0%}")
    m3.metric("Risk band", res["band"])
    low, high = BAND_EDGES
    {"Low": st.success, "Medium": st.warning, "High": st.error}[res["band"]](
        {"Low": f"Low risk: under {low:.0%} chance of a flat or lower listing.",
         "Medium": f"Medium risk: {low:.0%} to {high:.0%} chance of a flat or lower listing.",
         "High": f"High risk: {high:.0%} or more chance of a flat or lower listing."}[res["band"]])
    st.progress(float(res["p_positive"]), text="Probability of listing above the issue price")
    if res["gain_interval_pct"]:
        lo, hi = res["gain_interval_pct"]
        st.write(f"**80% range for the listing gain:** {lo:.0f}% to {hi:.0f}%")
        if res["price_interval"]:
            st.write(f"**Implied listing price:** ₹{res['implied_listing_price']:.2f} "
                     f"(80% range ₹{res['price_interval'][0]:.2f} to ₹{res['price_interval'][1]:.2f})")
    for note in res["notes"]:
        st.warning(note)
    st.caption(f"Model used: {res['model_used']}")

if gmp_pct is not None:
    st.subheader("Similar past IPOs")
    name = bucket_name(gmp_pct)
    row = bucket_stats(d).query("`GMP bucket` == @name")
    if not row.empty:
        r = row.iloc[0]
        st.write(f"IPOs with a final GMP in the same range (**{name}**): **{int(r['IPOs'])}**, "
                 f"{r['positive_rate']:.0%} listed positive, median gain {r['median_gain']:.1f}%, "
                 f"middle 80% of outcomes {r['gain_p10']:.0f}% to {r['gain_p90']:.0f}%.")
    near = (d.dropna(subset=["gmp_pct"]).assign(diff=lambda x: (x["gmp_pct"] - gmp_pct).abs()).nsmallest(8, "diff"))
    st.dataframe(near[["company_name", "listing_date", "gmp_pct", "overall_subscription", "listing_gain_pct", "outcome"]]
                 .rename(columns={"gmp_pct": "GMP %", "overall_subscription": "total subscription (x)",
                                  "listing_gain_pct": "actual listing gain %"}).round(1), hide_index=True)
footer()