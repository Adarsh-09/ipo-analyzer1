import py_compile
from pathlib import Path

p = Path("src/cleaning/validators.py")
s = p.read_text(encoding="utf-8")
Path("src/cleaning/validators.py.bak").write_text(s, encoding="utf-8")

def rep(old, new, count=1):
    global s
    assert s.count(old) == count, f"expected {count} match(es), found {s.count(old)}: {old[:70]!r}"
    s = s.replace(old, new)

rep("from src.cleaning.ipo_id import is_valid_ipo_id\n",
    '''from src.cleaning.ipo_id import is_valid_ipo_id

# Prediction stages. A "listing_eve" snapshot is taken the day before listing and is the only stage
# that may carry a GMP value without its own timestamp (the tracker gives one untimestamped final value).
VALID_STAGES = ("pre_close", "post_close", "listing_eve")
STAGES_REQUIRING_TIMESTAMPED_GMP = ("pre_close", "post_close")
MAX_EQUITY_ISSUE_PRICE = 10000.0  # SM-REIT / InvIT-style units priced above this are not equity IPOs
''')

rep("    1. prediction_stage must be 'pre_close' or 'post_close'.",
    "    1. prediction_stage must be 'pre_close', 'post_close' or 'listing_eve'.")
rep('if stage not in ("pre_close", "post_close"):', "if stage not in VALID_STAGES:", count=2)
rep('''message=f"Invalid prediction_stage '{stage}'. Must be 'pre_close' or 'post_close'.",''',
    '''message=f"Invalid prediction_stage '{stage}'. Must be one of {VALID_STAGES}.",''')

rep("        # Temporal Cutoff Check\n",
    '''        # GMP without its own timestamp is a listing-eve value: forbidden in earlier stages
        if stage in STAGES_REQUIRING_TIMESTAMPED_GMP and "gmp" in df.columns:
            if not _is_empty_or_na(row.get("gmp")) and _is_empty_or_na(row.get("gmp_recorded_at")):
                issues.append(
                    ValidationIssue(
                        level="ERROR",
                        category="STAGE",
                        row_index=int(idx),
                        ipo_id=ipo_id,
                        field="gmp",
                        message=(
                            f"GMP present in a {stage} row without gmp_recorded_at. "
                            "Untimestamped GMP is only allowed in listing_eve snapshots."
                        ),
                    )
                )

        # Temporal Cutoff Check
''')

OLD_PRICE = '''                        message=f"issue_price must be > 0. Found: {price_val}.",
                    )
                )
'''
rep(OLD_PRICE, OLD_PRICE + '''            elif price_val > MAX_EQUITY_ISSUE_PRICE:
                issues.append(
                    ValidationIssue(
                        level="ERROR",
                        category="IPO",
                        row_index=int(idx),
                        ipo_id=ipo_id,
                        field="issue_price",
                        message=(
                            f"issue_price {price_val:,.0f} exceeds {MAX_EQUITY_ISSUE_PRICE:,.0f}: "
                            "likely an SM-REIT/InvIT unit, not an equity IPO."
                        ),
                    )
                )
''')

p.write_text(s, encoding="utf-8")
py_compile.compile(str(p), doraise=True)
print("validators.py patched and compiles")