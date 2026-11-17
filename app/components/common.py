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
DISCLAIMER = ("IPOVision is a research and learning project, not investment advice. GMP is unofficial market "
              "sentiment, models can be wrong, and past listings do not guarantee future ones.")


@st.cache_data(show_spinner=False)
def load_ipos() -> pd.DataFrame:
    from src.cleaning import DatasetManager
    dm = DatasetManager()
    f, o = dm.load_dataset("ipo_features"), dm.load_dataset("ipo_outcomes")
    d = f.merge(o[["ipo_id", "listing_open_price", "listing_gain_pct", "listing_positive"]],
                on="ipo_id", validate="one_to_one")
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
    out = (g.groupby("GMP bucket", observed=True)
           .agg(IPOs=("ipo_id", "size"), positive_rate=("listing_positive", "mean"),
                median_gain=("listing_gain_pct", "median"),
                gain_p10=("listing_gain_pct", lambda s: s.quantile(0.10)),
                gain_p90=("listing_gain_pct", lambda s: s.quantile(0.90))).reset_index())
    return out.round({"positive_rate": 3, "median_gain": 1, "gain_p10": 1, "gain_p90": 1})


def footer() -> None:
    st.divider()
    st.caption(DISCLAIMER)