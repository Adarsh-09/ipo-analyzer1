import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MODEL_PATH = ROOT / "src/models/artifacts/ipovision_final.joblib"
BASE_PATH = ROOT / "data/interim/kaggle/model_base_v3.csv"
DISCLAIMER = (
    "IPOVision is a research and learning project, not investment advice. GMP is unofficial market "
    "sentiment, models can be wrong, and past listings do not guarantee future ones."
)


def apply_candy_theme() -> None:
    """Inject the Candy ('Joyful Pop') design system styling into the Streamlit app."""
    css = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,100..1000;1,9..40,100..1000&family=Inter:wght@400;500;600;700&display=swap');

    /* Global Typography */
    html, body, [class*="st-"], .stApp {
        font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    }

    /* Headings */
    h1, h2, h3, h4, .stHeading {
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
    }

    /* Buttons: Full Pill Radius + Tinted Shadow + Bouncy Hover */
    .stButton > button,
    .stDownloadButton > button,
    div[data-testid="stFormSubmitButton"] > button {
        border-radius: 9999px !important;
        font-weight: 600 !important;
        font-family: 'DM Sans', sans-serif !important;
        padding: 0.5rem 1.4rem !important;
        border: 1px solid #dcc8e0 !important;
        transition: all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1) !important;
        box-shadow: 0 2px 8px rgba(124, 82, 170, 0.08) !important;
    }

    .stButton > button:hover,
    .stDownloadButton > button:hover,
    div[data-testid="stFormSubmitButton"] > button:hover {
        transform: scale(1.03) !important;
        box-shadow: 0 6px 20px rgba(224, 64, 160, 0.22) !important;
        border-color: #e040a0 !important;
    }

    .stButton > button[kind="primary"],
    div[data-testid="stFormSubmitButton"] > button[kind="primary"] {
        background-color: #e040a0 !important;
        color: #ffffff !important;
        border: none !important;
        box-shadow: 0 4px 16px rgba(224, 64, 160, 0.28) !important;
    }

    .stButton > button[kind="primary"]:hover {
        background-color: #c9308c !important;
        transform: scale(1.04) !important;
        box-shadow: 0 8px 24px rgba(224, 64, 160, 0.35) !important;
    }

    /* Metric Cards: 16px radius, white fill, tinted shadow, hover lift */
    div[data-testid="stMetric"] {
        background: #ffffff !important;
        border: 1px solid #ece2ec !important;
        border-radius: 16px !important;
        padding: 16px 20px !important;
        box-shadow: 0 2px 10px rgba(124, 82, 170, 0.05) !important;
        transition: transform 0.2s ease, box-shadow 0.2s ease !important;
    }

    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px) scale(1.01) !important;
        box-shadow: 0 8px 22px rgba(124, 82, 170, 0.12) !important;
        border-color: #dcc8e0 !important;
    }

    div[data-testid="stMetricLabel"] {
        font-size: 0.8rem !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.04em !important;
        color: #7c52aa !important;
    }

    div[data-testid="stMetricValue"] {
        font-size: 1.85rem !important;
        font-weight: 700 !important;
        color: #2e1a28 !important;
        font-feature-settings: "tnum" on, "lnum" on !important;
    }

    /* Card Containers */
    .candy-card {
        background: #ffffff;
        border: 1px solid #ece2ec;
        border-radius: 16px;
        padding: 22px;
        box-shadow: 0 3px 14px rgba(124, 82, 170, 0.05);
        transition: all 0.2s ease;
        margin-bottom: 1.25rem;
    }

    .candy-card:hover {
        box-shadow: 0 8px 24px rgba(124, 82, 170, 0.1);
        border-color: #dcc8e0;
    }

    /* Pill Badges */
    .candy-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        line-height: 1.2;
    }

    .candy-badge-primary {
        background-color: #ffd6ee;
        color: #a02070;
        border: 1px solid #f0a0cc;
    }

    .candy-badge-secondary {
        background-color: #eedcff;
        color: #4a3068;
        border: 1px solid #c8a8e8;
    }

    .candy-badge-tertiary {
        background-color: #c8eaff;
        color: #005580;
        border: 1px solid #80d0f0;
    }

    .candy-badge-success {
        background-color: #dcfce7;
        color: #166534;
        border: 1px solid #86efac;
    }

    .candy-badge-warning {
        background-color: #fef9c3;
        color: #854d0e;
        border: 1px solid #fde047;
    }

    .candy-badge-error {
        background-color: #ffe4e6;
        color: #9f1239;
        border: 1px solid #fca5a5;
    }

    /* Form Inputs */
    input[type="text"], input[type="number"], .stSelectbox > div, .stMultiSelect > div {
        border-radius: 12px !important;
        border: 1px solid #dcc8e0 !important;
        background-color: #ffffff !important;
        transition: all 0.2s ease !important;
    }

    input[type="text"]:focus, input[type="number"]:focus {
        border-color: #e040a0 !important;
        box-shadow: 0 0 0 3px rgba(224, 64, 160, 0.2) !important;
    }

    /* Dataframe styling */
    div[data-testid="stDataFrame"] {
        border-radius: 14px !important;
        border: 1px solid #ece2ec !important;
        overflow: hidden !important;
        box-shadow: 0 2px 8px rgba(124, 82, 170, 0.04) !important;
    }

    /* Tabs */
    div[data-testid="stTabs"] button[role="tab"] {
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 600 !important;
        border-radius: 9999px !important;
        padding: 6px 16px !important;
        margin-right: 6px !important;
        transition: all 0.2s ease !important;
    }

    div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
        background-color: #ffd6ee !important;
        color: #a02070 !important;
    }

    /* Progress Bar */
    div[data-testid="stProgress"] > div > div > div > div {
        background: linear-gradient(90deg, #e040a0, #7c52aa) !important;
        border-radius: 9999px !important;
    }

    /* Alerts */
    div[data-testid="stAlert"] {
        border-radius: 14px !important;
        font-size: 0.92rem !important;
        border-width: 1px !important;
    }

    /* Sidebar Navigation */
    section[data-testid="stSidebar"] {
        border-right: 1px solid #ece2ec !important;
    }

    section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] li a {
        border-radius: 9999px !important;
        padding: 8px 16px !important;
        margin-bottom: 4px !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
    }

    section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] li a:hover {
        background-color: #f8eef8 !important;
        color: #e040a0 !important;
        transform: translateX(3px) !important;
    }

    section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] li a[aria-current="page"] {
        background-color: #ffd6ee !important;
        color: #a02070 !important;
        font-weight: 700 !important;
        box-shadow: 0 2px 8px rgba(224, 64, 160, 0.15) !important;
    }

    /* Stepper Cards */
    .candy-stepper-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 12px;
        margin-bottom: 1.5rem;
    }
    .candy-step-card {
        background: #ffffff;
        border: 1px solid #ece2ec;
        border-radius: 12px;
        padding: 12px 16px;
        display: flex;
        align-items: center;
        gap: 12px;
        transition: all 0.2s ease;
    }
    .candy-step-card.active {
        border-color: #e040a0;
        background: #fdf5fc;
        box-shadow: 0 2px 10px rgba(224, 64, 160, 0.12);
    }
    .candy-step-num {
        width: 28px;
        height: 28px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 12px;
        background: #eedcff;
        color: #4a3068;
    }
    .candy-step-card.active .candy-step-num {
        background: #e040a0;
        color: #ffffff;
    }
    .candy-step-text {
        font-size: 13px;
        font-weight: 600;
        color: #2e1a28;
    }
    .candy-step-desc {
        font-size: 11px;
        color: #907898;
    }

    /* Header Banner */
    .candy-header-banner {
        margin-bottom: 1.5rem;
        padding-bottom: 1rem;
        border-bottom: 1px solid #ece2ec;
    }
    .candy-header-meta {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 8px;
        flex-wrap: wrap;
    }
    .candy-header-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #2e1a28;
        letter-spacing: -0.025em;
        margin: 0;
        line-height: 1.2;
    }
    .candy-header-subtitle {
        font-size: 1rem;
        color: #604868;
        margin-top: 6px;
        line-height: 1.5;
        max-width: 820px;
    }
    .candy-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        display: inline-block;
    }
    .candy-dot-pink { background: #e040a0; box-shadow: 0 0 8px rgba(224, 64, 160, 0.6); }
    .candy-dot-green { background: #16a34a; box-shadow: 0 0 8px rgba(22, 163, 74, 0.6); }
    .candy-dot-purple { background: #7c52aa; box-shadow: 0 0 8px rgba(124, 82, 170, 0.6); }
    .candy-dot-blue { background: #0096cc; box-shadow: 0 0 8px rgba(0, 150, 204, 0.6); }

    /* Footer */
    .candy-footer {
        margin-top: 3rem;
        padding: 1.5rem 0;
        border-top: 1px solid #ece2ec;
        display: flex;
        flex-direction: column;
        gap: 8px;
        color: #907898;
        font-size: 0.85rem;
    }
    </style>
    """
    if hasattr(st, "html"):
        st.html(css)
    else:
        st.markdown(css, unsafe_allow_html=True)


def page_header(
    title: str,
    subtitle: str | None = None,
    badge: str | None = None,
    category: str | None = None,
    live_text: str | None = None,
    dot_color: str = "pink",
) -> None:
    """Render a unified Candy-style page header with badge, category, title, and subtitle."""
    apply_candy_theme()
    badges_html = []
    if badge:
        badges_html.append(f'<span class="candy-badge candy-badge-primary">{badge}</span>')
    if category:
        badges_html.append(f'<span class="candy-badge candy-badge-secondary">{category}</span>')
    if live_text:
        badges_html.append(
            f'<span style="font-size: 12px; color: #7c52aa; font-weight: 500; display: inline-flex; align-items: center; gap: 6px;">'
            f'<span class="candy-dot candy-dot-{dot_color}"></span>{live_text}</span>'
        )
    meta_row = f'<div class="candy-header-meta">{" ".join(badges_html)}</div>' if badges_html else ""
    sub_row = f'<p class="candy-header-subtitle">{subtitle}</p>' if subtitle else ""
    html = f"""
    <div class="candy-header-banner">
      {meta_row}
      <h1 class="candy-header-title">{title}</h1>
      {sub_row}
    </div>
    """
    if hasattr(st, "html"):
        st.html(html)
    else:
        st.markdown(html, unsafe_allow_html=True)


def workflow_stepper(steps: list[tuple[str, str]], active_idx: int = 1) -> None:
    """Render a visual horizontal stepper component for multi-stage workflows."""
    cards_html = []
    for idx, (step_title, step_desc) in enumerate(steps, start=1):
        is_active = (idx == active_idx)
        active_cls = "active" if is_active else ""
        cards_html.append(
            f'<div class="candy-step-card {active_cls}">'
            f'<div class="candy-step-num">{idx}</div>'
            f'<div><div class="candy-step-text">{step_title}</div><div class="candy-step-desc">{step_desc}</div></div>'
            f'</div>'
        )
    html = f'<div class="candy-stepper-grid">{"".join(cards_html)}</div>'
    if hasattr(st, "html"):
        st.html(html)
    else:
        st.markdown(html, unsafe_allow_html=True)


def candy_plotly_layout(fig, title: str | None = None, height: int | None = None):
    """Style Plotly figures to match the Candy design system."""
    layout_update = dict(
        template="plotly_white",
        font=dict(family="DM Sans, sans-serif", color="#2e1a28", size=12),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(254,247,255,0.4)",
        margin=dict(l=40, r=20, t=50 if title else 20, b=40),
    )
    if title:
        layout_update["title"] = dict(
            text=f"<b>{title}</b>",
            font=dict(family="DM Sans, sans-serif", size=15, color="#2e1a28"),
            x=0.0,
            xanchor="left",
        )
    if height:
        layout_update["height"] = height
    fig.update_layout(**layout_update)
    fig.update_xaxes(
        gridcolor="#f2e8f2",
        zerolinecolor="#dcc8e0",
        tickfont=dict(family="DM Sans, sans-serif", size=11, color="#604868"),
    )
    fig.update_yaxes(
        gridcolor="#f2e8f2",
        zerolinecolor="#dcc8e0",
        tickfont=dict(family="DM Sans, sans-serif", size=11, color="#604868"),
    )
    return fig


@st.cache_data(show_spinner=False)
def load_ipos() -> pd.DataFrame:
    from src.cleaning import DatasetManager
    dm = DatasetManager()
    f, o = dm.load_dataset("ipo_features"), dm.load_dataset("ipo_outcomes")
    d = f.merge(
        o[["ipo_id", "listing_open_price", "listing_gain_pct", "listing_positive"]],
        on="ipo_id",
        validate="one_to_one",
    )
    d["listing_date"] = pd.to_datetime(d["listing_date"])
    d["year"] = d["listing_date"].dt.year
    d["gmp_pct"] = d["gmp"] / d["issue_price"] * 100
    d["outcome"] = np.where(d["listing_positive"] == 1, "Positive", "Flat or lower")
    return d


@st.cache_resource(show_spinner=False)
def load_model():
    from src.models.final_model import load_bundle
    return load_bundle(MODEL_PATH) if MODEL_PATH.exists() else None


def require_model() -> dict:
    bundle = load_model()
    if bundle is None:
        st.error("Model file not found. Run `python root\\train_final_model.py` first.")
        st.stop()
    return bundle


def bucket_stats(d: pd.DataFrame) -> pd.DataFrame:
    """Outcomes by final-GMP bucket, computed from the data."""
    from src.models.final_model import GMP_BUCKETS
    g = d.dropna(subset=["gmp_pct"]).copy()
    edges = [GMP_BUCKETS[0][0]] + [b[1] for b in GMP_BUCKETS]
    g["GMP bucket"] = pd.cut(g["gmp_pct"], edges, labels=[b[2] for b in GMP_BUCKETS])
    out = (
        g.groupby("GMP bucket", observed=True)
        .agg(
            IPOs=("ipo_id", "size"),
            positive_rate=("listing_positive", "mean"),
            median_gain=("listing_gain_pct", "median"),
            gain_p10=("listing_gain_pct", lambda s: s.quantile(0.10)),
            gain_p90=("listing_gain_pct", lambda s: s.quantile(0.90)),
        )
        .reset_index()
    )
    return out.round({"positive_rate": 3, "median_gain": 1, "gain_p10": 1, "gain_p90": 1})


def footer() -> None:
    html = f"""
    <div class="candy-footer">
      <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;">
        <div style="display: flex; align-items: center; gap: 8px;">
          <span style="font-weight: 700; color: #e040a0;">IPOVision</span>
          <span style="color: #dcc8e0;">•</span>
          <span style="font-size: 12px; color: #7c52aa; font-weight: 500;">Joyful Analytics &amp; Empirical Model</span>
        </div>
        <div style="display: flex; align-items: center; gap: 6px;">
          <span class="candy-badge candy-badge-secondary" style="font-size: 10px; padding: 2px 8px;">Analyst Terminal v1.4.2</span>
        </div>
      </div>
      <p style="margin: 4px 0 0 0; font-size: 12px; color: #907898; line-height: 1.5;">{DISCLAIMER}</p>
    </div>
    """
    if hasattr(st, "html"):
        st.html(html)
    else:
        st.markdown(html, unsafe_allow_html=True)
