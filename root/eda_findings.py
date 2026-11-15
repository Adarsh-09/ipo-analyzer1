import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.cleaning import DatasetManager

FIG, EDA = ROOT / "reports/figures", ROOT / "reports/eda"
FIG.mkdir(parents=True, exist_ok=True); EDA.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"figure.dpi": 120, "axes.grid": True, "grid.alpha": 0.25,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.titlesize": 10})
POS, NEG = "#4C78A8", "#E45756"

# ---------- load processed tables + market/momentum columns ----------
dm = DatasetManager()
f, o = dm.load_dataset("ipo_features"), dm.load_dataset("ipo_outcomes")
d = f.merge(o[["ipo_id", "listing_open_price", "listing_gain_pct", "listing_positive"]],
            on="ipo_id", validate="one_to_one")
d["listing_date"] = pd.to_datetime(d["listing_date"])
d["year"] = d["listing_date"].dt.year
d["gmp_pct"] = d["gmp"] / d["issue_price"] * 100
mb = pd.read_csv(ROOT / "data/interim/kaggle/model_base_v2.csv", parse_dates=["listing_date"])
n = len(d)
d = d.merge(mb[["listing_date", "company_name", "nifty_ret_5d", "nifty_ret_20d", "vix_level",
                "recent_gain_mean10", "data_source"]], on=["listing_date", "company_name"],
            how="left", validate="one_to_one")
assert len(d) == n

d["sub_bucket"] = pd.cut(d["overall_subscription"], [0, 1, 3, 10, 30, 100, np.inf],
                         labels=["<1x", "1-3x", "3-10x", "10-30x", "30-100x", ">100x"], right=False)
d["gmp_bucket"] = pd.cut(d["gmp_pct"], [-np.inf, 0, 10, 30, 60, np.inf],
                         labels=["<=0", "0-10%", "10-30%", "30-60%", ">60%"])
d["size_bucket"] = pd.cut(d["issue_size_cr"], [0, 250, 500, 1000, 2500, 5000, np.inf],
                          labels=["<250", "250-500", "500-1k", "1k-2.5k", "2.5k-5k", ">5k"])

def table(col):
    return (d.groupby(col, observed=True)
              .agg(ipos=("ipo_id", "size"), positive_rate=("listing_positive", "mean"),
                   median_gain=("listing_gain_pct", "median"), mean_gain=("listing_gain_pct", "mean"))
              .reset_index())

def save(fig, name):
    fig.tight_layout(); fig.savefig(FIG / f"{name}.png"); plt.close(fig)

# ---------- 1) distribution of listing gains ----------
fig, ax = plt.subplots(figsize=(8, 4.5))
ax.hist(d["listing_gain_pct"].clip(-60, 150), bins=55, color=POS)
ax.axvline(0, color="k", lw=1)
ax.axvline(d["listing_gain_pct"].median(), color=NEG, ls="--", label=f"median {d['listing_gain_pct'].median():.1f}%")
ax.set(title=f"Listing gain distribution (n={len(d)}, {d['listing_positive'].mean():.0%} positive; clipped for display)",
       xlabel="listing gain %", ylabel="IPOs"); ax.legend()
save(fig, "01_gain_distribution")

# ---------- 2) by year ----------
yr = (d.groupby("year").agg(ipos=("ipo_id", "size"), positive_rate=("listing_positive", "mean"),
                            median_gain=("listing_gain_pct", "median"), mean_gain=("listing_gain_pct", "mean"))
        .reset_index())
fig, ax = plt.subplots(figsize=(8, 4.5))
ax.bar(yr["year"], yr["positive_rate"] * 100, color=POS)
for _, r in yr.iterrows():
    ax.text(r["year"], r["positive_rate"] * 100 + 1.5, f"n={int(r['ipos'])}", ha="center", fontsize=8)
ax2 = ax.twinx(); ax2.plot(yr["year"], yr["median_gain"], color=NEG, marker="o"); ax2.grid(False)
ax2.set_ylabel("median gain %", color=NEG)
ax.set(title="Positive-listing rate (bars) and median gain (line) by year", xlabel="listing year",
       ylabel="positive %", ylim=(0, 115))
save(fig, "02_by_year")

# ---------- 3) subscription vs gain ----------
s = d[d["overall_subscription"] > 0]
rho_sub = spearmanr(s["overall_subscription"], s["listing_gain_pct"])[0]
fig, ax = plt.subplots(figsize=(8, 4.5))
ax.scatter(s["overall_subscription"], s["listing_gain_pct"].clip(-60, 300),
           c=np.where(s["listing_positive"] == 1, POS, NEG), s=14, alpha=0.6)
ax.set_xscale("log"); ax.axhline(0, color="k", lw=0.8); ax.axvline(1, color="gray", ls=":")
ax.set(title=f"Total subscription vs listing gain (Spearman {rho_sub:.2f})",
       xlabel="total subscription (x, log scale)", ylabel="listing gain %")
save(fig, "03_subscription_vs_gain")

# ---------- 4) how accurate is GMP? ----------
g = d.dropna(subset=["gmp_pct"]).copy()
g["resid"] = g["listing_gain_pct"] - g["gmp_pct"]
rho_gmp = spearmanr(g["gmp_pct"], g["listing_gain_pct"])[0]
fig, axs = plt.subplots(1, 2, figsize=(11, 4.5))
axs[0].scatter(g["gmp_pct"], g["listing_gain_pct"], s=14, alpha=0.6, color=POS)
lim = [min(g["gmp_pct"].min(), g["listing_gain_pct"].min()), max(g["gmp_pct"].max(), g["listing_gain_pct"].max())]
axs[0].plot(lim, lim, "k--", lw=1, label="GMP = actual gain"); axs[0].legend()
axs[0].set(title=f"GMP% vs actual gain (Spearman {rho_gmp:.2f}, n={len(g)})",
           xlabel="final GMP, % of issue price", ylabel="listing gain %")
axs[1].hist(g["resid"].clip(-60, 60), bins=50, color=POS); axs[1].axvline(0, color="k", lw=1)
axs[1].set(title=f"Actual gain minus GMP% (median {g['resid'].median():.1f} pts)",
           xlabel="points (clipped at +/-60)", ylabel="IPOs")
save(fig, "04_gmp_accuracy")

# ---------- 5) positive rate by bucket ----------
fig, axs = plt.subplots(1, 3, figsize=(14, 4.2), sharey=True)
for ax, col, title in zip(axs, ["sub_bucket", "gmp_bucket", "size_bucket"],
                          ["total subscription", "final GMP % of issue price", "issue size (crore)"]):
    t = table(col)
    ax.bar(t[col].astype(str), t["positive_rate"] * 100, color=POS)
    for i, r in t.iterrows():
        ax.text(i, r["positive_rate"] * 100 + 1.5, f"n={int(r['ipos'])}\nmed {r['median_gain']:.0f}%",
                ha="center", fontsize=7)
    ax.set(title=f"Positive-listing rate by {title}", ylim=(0, 125)); ax.tick_params(axis="x", labelrotation=30)
axs[0].set_ylabel("positive %")
save(fig, "05_buckets")

# ---------- 6) rank-correlation heatmap ----------
cols = ["listing_gain_pct", "gmp_pct", "overall_subscription", "qib_subscription", "nii_subscription",
        "retail_subscription", "issue_size_cr", "nifty_ret_5d", "nifty_ret_20d", "vix_level", "recent_gain_mean10"]
C = d[cols].corr(method="spearman")
fig, ax = plt.subplots(figsize=(8, 6.5))
im = ax.imshow(C, vmin=-1, vmax=1, cmap="RdBu_r"); ax.grid(False)
ax.set_xticks(range(len(cols))); ax.set_xticklabels(cols, rotation=60, ha="right", fontsize=8)
ax.set_yticks(range(len(cols))); ax.set_yticklabels(cols, fontsize=8)
for i in range(len(cols)):
    for j in range(len(cols)):
        ax.text(j, i, f"{C.iloc[i, j]:.2f}", ha="center", va="center", fontsize=7)
fig.colorbar(im, shrink=0.8); ax.set_title("Spearman correlations")
save(fig, "06_correlations")

# ---------- 7) market conditions ----------
m = d.dropna(subset=["nifty_ret_20d"])
rho_mkt = spearmanr(m["nifty_ret_20d"], m["listing_gain_pct"])[0]
fig, ax = plt.subplots(figsize=(8, 4.5))
ax.scatter(m["nifty_ret_20d"], m["listing_gain_pct"].clip(-60, 150), s=14, alpha=0.6, color=POS)
ax.axhline(0, color="k", lw=0.8)
ax.set(title=f"Nifty 20-day return before listing vs gain (Spearman {rho_mkt:.2f})",
       xlabel="Nifty 20-day return %", ylabel="listing gain %")
save(fig, "07_market_vs_gain")

# ---------- computed findings (numbers come from the data, not from me) ----------
def md(df):
    def fmt(v):
        if isinstance(v, (float, np.floating)):
            return str(int(v)) if float(v).is_integer() else f"{v:.2f}"
        return str(v)
    rows = ["| " + " | ".join(map(str, df.columns)) + " |", "|" + "---|" * len(df.columns)]
    for _, r in df.iterrows():
        rows.append("| " + " | ".join(fmt(v) for v in r) + " |")
    return "\n".join(rows)

gain = d["listing_gain_pct"]
up = g[g["gmp_pct"] > 0]; down = g[g["gmp_pct"] <= 0]
tmp = d.assign(date=d["listing_date"].dt.strftime("%Y-%m-%d"))
gg = g.assign(date=g["listing_date"].dt.strftime("%Y-%m-%d"))
show = ["date", "company_name", "issue_price", "listing_gain_pct", "overall_subscription", "gmp_pct"]
corr = C["listing_gain_pct"].drop("listing_gain_pct").sort_values(ascending=False).rename_axis("feature").reset_index(name="spearman")

L = ["# IPOVision - EDA findings (auto-generated from data/processed)", "",
     f"- IPOs: **{len(d)}** ({d['year'].min()}-{d['year'].max()}); positive listings **{d['listing_positive'].mean():.1%}**",
     f"- Gain: median {gain.median():.1f}%, mean {gain.mean():.1f}%, 5th pct {gain.quantile(.05):.1f}%, 95th pct {gain.quantile(.95):.1f}%, min {gain.min():.1f}%, max {gain.max():.1f}%",
     f"- IPOs within +/-2% of the issue price (exposed to NSE/BSE open-price label noise): {(gain.abs() <= 2).mean():.1%}",
     f"- GMP present for {d['gmp_pct'].notna().sum()} IPOs; total subscription for {d['overall_subscription'].notna().sum()}", "",
     "## By year", md(yr), "",
     "## By total subscription", md(table("sub_bucket")), "",
     "## By final GMP % of issue price", md(table("gmp_bucket")), "",
     "## By issue size (crore)", md(table("size_bucket")), "",
     "## GMP accuracy",
     f"- n={len(g)} | MAE {g['resid'].abs().mean():.2f} pts | median residual (actual minus GMP) {g['resid'].median():.2f} | Spearman {rho_gmp:.3f}",
     f"- GMP > 0 in {len(up)} IPOs; {(up['listing_gain_pct'] <= 0).sum()} of them ({(up['listing_gain_pct'] <= 0).mean():.1%}) still listed flat or lower",
     f"- GMP <= 0 in {len(down)} IPOs; {(down['listing_gain_pct'] > 0).sum()} of them listed positive", "",
     "## Spearman correlation with listing gain", md(corr), "",
     "## 10 worst listings", md(tmp.nsmallest(10, "listing_gain_pct")[show]), "",
     "## 10 biggest GMP misses (actual gain minus GMP %)",
     md(gg.loc[g["resid"].abs().nlargest(10).index, show + ["resid"]])]
text = "\n".join(L)
(EDA / "eda_findings.md").write_text(text, encoding="utf-8")
print(text)
print("\nFigures saved to", FIG)