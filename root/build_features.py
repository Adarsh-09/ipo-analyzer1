from pathlib import Path
import numpy as np
import pandas as pd
import yfinance as yf

SRC = Path("E:/ipo-analyzer1/data/interim/kaggle/kaggle_clean_candidates.csv")
OUT = Path("E:/ipo-analyzer1/data/interim/kaggle/model_base.csv")
MKT = Path("E:/ipo-analyzer1/data/raw/market_context.csv")
MIN_YEAR = 2017

df = pd.read_csv(SRC).assign(listing_date=lambda d: pd.to_datetime(d["listing_date"]))
df["listing_date"] = df["listing_date"].astype("datetime64[ns]")
df = df.sort_values("listing_date").reset_index(drop=True)

# 1) Recent IPO momentum (only listings strictly before this listing date; uses full history)
def momentum(n):
    means, pos = [], []
    for d in df["listing_date"]:
        prior = df.loc[df["listing_date"] < d].tail(n)
        if len(prior) < 5:
            means.append(np.nan); pos.append(np.nan)
        else:
            means.append(prior["listing_gain_pct"].mean())
            pos.append(prior["listing_positive"].mean())
    return means, pos

df["recent_gain_mean10"], df["recent_pos_rate10"] = momentum(10)
df["recent_gain_mean30"], _ = momentum(30)

# 2) Market context from the last trading day before listing
if MKT.exists():
    mkt = pd.read_csv(MKT, index_col=0, parse_dates=True)
else:
    def close(ticker):
        x = yf.download(ticker, start="2009-10-01", end="2026-07-01",
                        auto_adjust=False, progress=False)["Close"]
        return x.iloc[:, 0] if isinstance(x, pd.DataFrame) else x
    mkt = pd.concat({"nifty": close("^NSEI"), "vix": close("^INDIAVIX")}, axis=1)
    MKT.parent.mkdir(parents=True, exist_ok=True)
    mkt.to_csv(MKT)

mkt.index = pd.to_datetime(mkt.index).tz_localize(None).astype("datetime64[ns]")
mkt = mkt.sort_index().dropna(subset=["nifty"])
mkt["vix"] = mkt["vix"].ffill()
mkt["nifty_ret_5d"] = mkt["nifty"].pct_change(5) * 100
mkt["nifty_ret_20d"] = mkt["nifty"].pct_change(20) * 100
mkt["vix_level"] = mkt["vix"]
mkt["vix_change_5d"] = mkt["vix"].pct_change(5) * 100
mkt.index.name = "mkt_date"
feat = mkt[["nifty_ret_5d", "nifty_ret_20d", "vix_level", "vix_change_5d"]].reset_index()

df = pd.merge_asof(df, feat, left_on="listing_date", right_on="mkt_date",
                   direction="backward", allow_exact_matches=False)

# 3) Size and subscription features
df["log_issue_size"] = np.log(df["issue_size_cr"])
for c in ["qib", "nii", "retail", "total"]:
    df[f"log_{c}"] = np.log1p(df[f"{c}_sub"])

out = df[df["listing_year"] >= MIN_YEAR].copy()
out.to_csv(OUT, index=False)

print("Rows:", len(out), "| years:", out["listing_year"].min(), "-", out["listing_year"].max())
feats = ["log_issue_size", "recent_gain_mean10", "recent_pos_rate10", "recent_gain_mean30",
         "nifty_ret_5d", "nifty_ret_20d", "vix_level", "vix_change_5d",
         "log_qib", "log_nii", "log_retail", "log_total"]
print("\nMissing values:\n", out[feats].isna().sum())
print("\nSpearman correlation with listing_gain_pct:\n",
      out[feats + ["listing_gain_pct"]].corr(method="spearman")["listing_gain_pct"].drop("listing_gain_pct").round(3))
print("\nSaved to", OUT)