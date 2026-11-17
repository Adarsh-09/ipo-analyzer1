import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import pandas as pd
import plotly.express as px
import streamlit as st

from app.components.common import footer
from src.fundamental_analysis.scoring import FundamentalInputs, ListingInputs, score_fundamental, score_listing

st.set_page_config(page_title="Checklist scores - IPOVision", page_icon="📈", layout="wide")
st.title("Checklist scores")
st.caption("Two 100-point scores from an IPO analysis checklist. The weights come from the checklist; the mapping from "
           "numbers to points is a transparent heuristic, not a fitted model. Leave a field blank if you don't know it: "
           "it is left out and the score is rescaled over what was scored.")


def num(label, key, help=None):
    raw = st.text_input(label, key=key, help=help, placeholder="blank = unknown").strip().replace(",", "")
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        st.error(f"'{raw}' is not a number")
        return None


def series(label, key, help=None):
    raw = st.text_input(label, key=key, help=help, placeholder="e.g. 450, 520, 610")
    vals = []
    for part in raw.replace(";", ",").split(","):
        part = part.strip().replace(" ", "")
        if part:
            try:
                vals.append(float(part))
            except ValueError:
                st.error(f"'{part}' is not a number")
                return None
    return vals or None


def rating(label, key, help=None):
    v = st.selectbox(label, ["not rated", 0, 1, 2, 3, 4, 5], key=key, help=help)
    return None if v == "not rated" else float(v)


def show(res, title):
    if res["score"] is None:
        st.info("Enter at least one input to get a score.")
        return
    a, b, c = st.columns(3)
    a.metric(title, f"{res['score']:.0f} / 100")
    b.metric("Band", res["band"])
    c.metric("Checklist covered", f"{res['coverage']:.0%}")
    if res["partial"]:
        st.warning("Less than 60% of the checklist could be scored, so treat this as a partial reading.")
    rows = [{"Category": k, "Weight": v["weight"], "Points earned": v["points"],
             "Status": "scored" if v["score"] is not None else "no input"} for k, v in res["categories"].items()]
    df = pd.DataFrame(rows)
    st.dataframe(df.round(1), hide_index=True)
    scored = df.dropna(subset=["Points earned"])
    if not scored.empty:
        st.plotly_chart(px.bar(scored, x="Points earned", y="Category", orientation="h", text_auto=".1f",
                               hover_data=["Weight"], title="Points earned by category"))
    for flag in res["red_flags"]:
        st.warning(flag)
    if not res["red_flags"] and not res["partial"] and res["categories"]:
        st.success("No red flags triggered by the inputs given.")


t_list, t_fund = st.tabs(["Listing score", "Fundamental score"])
with t_list:
    st.markdown("Short-term view: how supportive are demand and sentiment for a listing gain?")
    c1, c2 = st.columns(2)
    with c1:
        gmp = num("Final GMP, % of issue price", "l_gmp")
        qib = num("QIB subscription (times)", "l_qib")
        tot = num("Total subscription (times)", "l_tot")
        size = num("Issue size (₹ crore)", "l_size")
    with c2:
        nifty = num("Nifty 50 return over the last 20 trading days (%)", "l_nifty")
        prem = num("IPO P/E premium to listed peers (%)", "l_prem")
        sector = rating("Sector sentiment (0 weak ... 5 strong)", "l_sector")
    show(score_listing(ListingInputs(gmp_pct=gmp, qib_sub=qib, total_sub=tot, nifty_ret_20d=nifty, pe_premium_pct=prem,
                                     sector_sentiment_rating=sector, issue_size_cr=size)), "Listing score")
    st.caption("The Predict page turns the GMP into a measured probability. This score is the checklist's own view.")

with t_fund:
    st.markdown("Long-term view of the business. Qualitative items are your own judgement on a 0 to 5 scale.")
    c1, c2, c3 = st.columns(3)
    with c1:
        revenue = series("Revenue, last 3-5 years (₹ cr, oldest first)", "f_rev")
        pat = series("Profit after tax, same years (₹ cr)", "f_pat")
        margin = num("EBITDA margin (%)", "f_margin")
        roe = num("ROE (%)", "f_roe")
        roce = num("ROCE (%)", "f_roce")
        de = num("Debt / equity", "f_de")
        icov = num("Interest coverage (times)", "f_icov")
    with c2:
        cfo = num("Operating cash flow, latest year (₹ cr)", "f_cfo")
        inv = num("Inventory days, latest year", "f_inv")
        inv_prev = num("Inventory days, previous year", "f_invp")
        biz = rating("Business quality", "f_biz", "Easy to understand, competitive advantage, customer concentration")
        mgmt = rating("Management and governance", "f_mgmt")
        hold = num("Promoter holding after IPO (%)", "f_hold")
        pledge = num("Promoter shares pledged (%)", "f_pledge")
        lit = rating("Litigation severity (0 none ... 5 severe)", "f_lit")
    with c3:
        pm = num("Peer median EBITDA margin (%)", "f_pm")
        pr = num("Peer median ROE (%)", "f_pr")
        pg = num("Peer median revenue growth (%)", "f_pg")
        pe = num("IPO P/E", "f_pe")
        ppe = num("Peer median P/E", "f_ppe")
        ofs = num("Offer for sale share of the issue (%)", "f_ofs")
        uof = rating("Use of funds (0 weak ... 5 value-creating)", "f_uof")
    res = score_fundamental(FundamentalInputs(
        revenue=revenue, pat=pat, ebitda_margin_pct=margin, roe_pct=roe, roce_pct=roce, debt_to_equity=de,
        interest_coverage=icov, cfo=cfo, inventory_days=inv, inventory_days_prev=inv_prev, business_quality_rating=biz,
        management_rating=mgmt, promoter_holding_post_pct=hold, promoter_pledge_pct=pledge, litigation_severity=lit,
        peer_ebitda_margin_pct=pm, peer_roe_pct=pr, peer_revenue_growth_pct=pg, pe_ratio=pe, peer_pe_ratio=ppe,
        ofs_pct=ofs, use_of_funds_rating=uof))
    show(res, "Fundamental score")
    m = res["metrics"]
    if m["revenue_cagr_pct"] is not None:
        st.caption(f"Revenue CAGR {m['revenue_cagr_pct']:.1f}%"
                   + (f" | profit CAGR {m['pat_cagr_pct']:.1f}%" if m["pat_cagr_pct"] is not None else "")
                   + (f" | CFO/PAT {m['cfo_to_pat']:.2f}" if m["cfo_to_pat"] is not None else "")
                   + (f" | P/E premium {m['pe_premium_pct']:.0f}%" if m["pe_premium_pct"] is not None else ""))
footer()