import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.cleaning import DatasetManager

dm = DatasetManager()
f, o = dm.load_dataset("ipo_features"), dm.load_dataset("ipo_outcomes")
d = f.merge(o[["ipo_id", "listing_gain_pct", "listing_positive"]], on="ipo_id", validate="one_to_one")
d["listing_date"] = pd.to_datetime(d["listing_date"]); d["year"] = d["listing_date"].dt.year
d["gmp_pct"] = d["gmp"] / d["issue_price"] * 100
mb = pd.read_csv(ROOT / "data/interim/kaggle/model_base_v2.csv", parse_dates=["listing_date"])
d = d.merge(mb[["listing_date", "company_name", "nifty_ret_20d", "recent_gain_mean10"]],
            on=["listing_date", "company_name"], how="left", validate="one_to_one")
d["sub_bucket"] = pd.cut(d["overall_subscription"], [0, 1, 3, 10, 30, 100, np.inf],
                         labels=["<1x", "1-3x", "3-10x", "10-30x", "30-100x", ">100x"], right=False)
d["gmp_bucket"] = pd.cut(d["gmp_pct"], [-np.inf, 0, 10, 30, 60, np.inf],
                         labels=["<=0", "0-10%", "10-30%", "30-60%", ">60%"])

def md(df):
    def fmt(v):
        if isinstance(v, (float, np.floating)):
            return str(int(v)) if float(v).is_integer() else f"{v:.2f}"
        return str(v)
    rows = ["| " + " | ".join(map(str, df.columns)) + " |", "|" + "---|" * len(df.columns)]
    for _, r in df.iterrows():
        rows.append("| " + " | ".join(fmt(v) for v in r) + " |")
    return "\n".join(rows)

g = d.dropna(subset=["gmp_pct", "overall_subscription"]).copy()
rate = g.pivot_table(index="gmp_bucket", columns="sub_bucket", values="listing_positive", aggfunc="mean", observed=False)
cnt = g.pivot_table(index="gmp_bucket", columns="sub_bucket", values="listing_positive", aggfunc="size", observed=False)

fig, ax = plt.subplots(figsize=(8, 5))
im = ax.imshow(rate.values * 100, vmin=0, vmax=100, cmap="RdYlGn"); ax.grid(False)
ax.set_xticks(range(rate.shape[1])); ax.set_xticklabels(rate.columns); ax.set_yticks(range(rate.shape[0])); ax.set_yticklabels(rate.index)
for i in range(rate.shape[0]):
    for j in range(rate.shape[1]):
        n = cnt.iloc[i, j]
        ax.text(j, i, "-" if (pd.isna(n) or n == 0) else f"{rate.iloc[i, j]*100:.0f}%\nn={int(n)}", ha="center", va="center", fontsize=8)
ax.set(title="Positive-listing rate by GMP bucket x subscription bucket", xlabel="total subscription", ylabel="final GMP % of issue price")
fig.colorbar(im, shrink=0.8, label="positive %"); fig.tight_layout()
fig.savefig(ROOT / "reports/figures/08_gmp_x_subscription.png", dpi=120); plt.close(fig)

# false-comfort cohort: GMP > 0 but listing flat or lower
up = g[g["gmp_pct"] > 0].copy()
up["outcome"] = np.where(up["listing_positive"] == 1, "listed positive", "flat or lower")
prof = (up.groupby("outcome")[["gmp_pct", "overall_subscription", "qib_subscription", "issue_size_cr",
                               "nifty_ret_20d", "recent_gain_mean10"]].median().reset_index())
by_year = pd.crosstab(up["year"], up["outcome"]).reset_index()
low_gmp = up[up["gmp_pct"] <= 10].groupby("sub_bucket", observed=True)["listing_positive"].agg(ipos="size", positive_rate="mean").reset_index()

near = d["listing_gain_pct"].abs() <= 2
clean = d[~near]
show = ["listing_date", "company_name", "issue_price", "listing_gain_pct", "overall_subscription", "gmp_pct"]
heavy_loss = d[(d["overall_subscription"] >= 30) & (d["listing_gain_pct"] <= 0)][show].sort_values("listing_gain_pct")
light_gain = d[(d["overall_subscription"] < 3) & (d["listing_gain_pct"] >= 20)][show].sort_values("listing_gain_pct", ascending=False)
for t in (heavy_loss, light_gain):
    t["listing_date"] = t["listing_date"].dt.strftime("%Y-%m-%d")

L = ["# IPOVision - EDA follow-up (auto-generated)", "",
     "## Positive rate: GMP bucket x subscription bucket (figure 08)", md(rate.round(2).reset_index()), "",
     "Counts:", md(cnt.reset_index()), "",
     f"## False-comfort cohort: GMP > 0 but listed flat or lower ({(up['listing_positive'] == 0).sum()} of {len(up)})",
     "Median profile by outcome:", md(prof), "",
     "By year:", md(by_year), "",
     "Positive rate when GMP is between 0 and 10%, by subscription bucket:", md(low_gmp), "",
     "## Label-noise exposure",
     f"- IPOs within +/-2% of issue price: {int(near.sum())} of {len(d)} ({near.mean():.1%})",
     f"- Positive share among them: {d.loc[near, 'listing_positive'].mean():.1%}; positive share of the remaining {len(clean)}: {clean['listing_positive'].mean():.1%}", "",
     f"## Heavily subscribed (>=30x) yet listed flat or lower: {len(heavy_loss)} IPOs", md(heavy_loss.head(15)), "",
     f"## Weakly subscribed (<3x) yet gained 20%+: {len(light_gain)} IPOs", md(light_gain.head(15))]
text = "\n".join(L)
(ROOT / "reports/eda/eda_followup.md").write_text(text, encoding="utf-8")
print(text)