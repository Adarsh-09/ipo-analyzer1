from pathlib import Path

p = Path("root/build_v3.py")
s = p.read_text(encoding="utf-8")

def rep(old, new):
    global s
    if new in s:
        return
    if old in s:
        s = s.replace(old, new)
        return

    # Some versions may already have a partially updated variant, or the file may
    # already include the final version. Treat those as already applied instead of
    # crashing out on a one-off patch script.
    alt = old.replace('reit|invit|trust|fund|real estate|propshare|office parks',
                      'reit|invit|trust|fund|real estate|propshare|property share|office parks|infrastructure fund')
    if alt in s:
        s = s.replace(alt, new)
        return

    raise AssertionError(f"not found exactly once: {old[:70]!r}")

# 1) word-boundary name rule (keeps SBI Funds Management, still catches REIT/InvIT/trust units)
rep(r'NON_EQUITY = r"reit|invit|trust|fund|real estate|propshare|office parks"',
    r'NON_EQUITY = r"\breit\b|invit|\btrust\b|real estate|propshare|property share|office parks|infrastructure fund"')

# 2) where Kaggle's total subscription disagrees with the tracker by >25%, use the tracker's value
rep('k = k.merge(best[["kid", "tid", "gmp_rs", "gmp_pct_of_issue", "symbol"]], on="kid", how="left")\n'
    'assert len(k) == n0 and k["tid"].dropna().is_unique',
    '''k = k.merge(best[["kid", "tid", "gmp_rs", "gmp_pct_of_issue", "symbol", "total_sub_t"]], on="kid", how="left")
assert len(k) == n0 and k["tid"].dropna().is_unique
rel = ((k["total_sub"] - k["total_sub_t"]).abs() / k["total_sub"]).replace([np.inf], 1.0).fillna(0)
k["sub_conflict"] = rel > 0.25
k.loc[k["sub_conflict"], "total_sub"] = k.loc[k["sub_conflict"], "total_sub_t"]
k.loc[k["sub_conflict"], ["qib_sub", "nii_sub", "retail_sub"]] = np.nan
k = k.drop(columns=["total_sub_t"])''')

rep('df["listing_year"] = df["listing_date"].dt.year\n',
    'df["listing_year"] = df["listing_date"].dt.year\ndf["sub_conflict"] = df["sub_conflict"].fillna(False).astype(bool)\n')

rep('print(f"Accepted matches where issue size differs >10% or subscription differs >25%: {len(flag)}")',
    '''print(f"Accepted matches where issue size differs >10% or subscription differs >25%: {len(flag)}")
print(f"  tracker subscription higher than Kaggle in {(flag['total_sub_t'] > flag['total_sub']).mean():.0%} of them | rows marked sub_conflict: {int(out['sub_conflict'].sum())}")''')

p.write_text(s, encoding="utf-8")
print("build_v3.py patched")