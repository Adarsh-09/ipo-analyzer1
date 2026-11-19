"""IPOVision scoring (Phase 6): the two 100-point scores from the IPO analysis checklist.

The category weights come from the checklist. The mapping from raw numbers to 0-1 sub-scores is a transparent
heuristic, not a fitted model. A missing input never counts as zero: a category with no data is left out and the
score is rescaled over the weight that could be scored (reported as `coverage`).
"""
from __future__ import annotations

import re
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

FUNDAMENTAL_WEIGHTS: Dict[str, float] = {
    "Business quality": 15, "Revenue and profit growth": 15, "Profitability": 10, "Debt and balance sheet": 10,
    "Cash flow and working capital": 10, "Promoter and management": 10, "Peer comparison": 10,
    "Valuation": 15, "IPO structure and use of funds": 5}
LISTING_WEIGHTS: Dict[str, float] = {
    "GMP": 30, "QIB subscription": 25, "Total subscription": 15, "Market sentiment": 10,
    "IPO valuation": 10, "Sector sentiment": 5, "Issue size and liquidity": 5}
FUNDAMENTAL_BANDS = ((80, "Excellent"), (70, "Good"), (60, "Average"), (50, "Weak"), (float("-inf"), "Avoid / caution"))
LISTING_BANDS = ((80, "Strong listing setup"), (70, "Good"), (60, "Uncertain"), (float("-inf"), "Weak"))
PARTIAL_BELOW = 0.60            # below this share of the checklist, the result is marked partial
GROWTH_POINTS = [(0, 0.0), (10, 0.4), (20, 0.8), (30, 1.0)]


# ------------------------------------------------------------------ helpers
def _missing(x) -> bool:
    return x is None or (isinstance(x, float) and math.isnan(x))


def interp(x, points) -> Optional[float]:
    """Piecewise-linear map of x through (x, score) points; clamps outside the range; None if x is missing."""
    if _missing(x):
        return None
    x, pts = float(x), sorted(points)
    if x <= pts[0][0]:
        return float(pts[0][1])
    if x >= pts[-1][0]:
        return float(pts[-1][1])
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            return float(y0 + (y1 - y0) * (x - x0) / (x1 - x0))
    return None


def mean_available(values) -> Optional[float]:
    v = [x for x in values if x is not None]
    return sum(v) / len(v) if v else None


def _wmean(pairs) -> Optional[float]:
    pairs = [(w, s) for w, s in pairs if s is not None]
    total = sum(w for w, _ in pairs)
    return None if total == 0 else sum(w * s for w, s in pairs) / total


def _clean(series) -> List[float]:
    return [float(v) for v in (series or []) if not _missing(v)]


def cagr(series) -> Optional[float]:
    """Compound annual growth in %, oldest value first. Undefined (None) if an end value is not positive."""
    s = _clean(series)
    if len(s) < 2 or s[0] <= 0 or s[-1] <= 0:
        return None
    return ((s[-1] / s[0]) ** (1.0 / (len(s) - 1)) - 1.0) * 100.0


def _rating(x) -> Optional[float]:
    return None if _missing(x) else min(max(float(x), 0.0), 5.0) / 5.0


def _diff(a, b) -> Optional[float]:
    return None if _missing(a) or _missing(b) else float(a) - float(b)


def band_for(score: float, bands) -> str:
    for floor, name in bands:
        if score >= floor:
            return name
    return bands[-1][1]


def _combine(scores: Dict[str, Optional[float]], weights: Dict[str, float], bands) -> dict:
    cats, avail, pts = {}, 0.0, 0.0
    for name, w in weights.items():
        s = scores.get(name)
        s = None if s is None else min(max(s, 0.0), 1.0)
        cats[name] = {"weight": w, "score": s, "points": None if s is None else s * w}
        if s is not None:
            avail += w
            pts += s * w
    coverage = avail / sum(weights.values())
    score = None if avail == 0 else 100.0 * pts / avail
    return {"score": score, "band": None if score is None else band_for(score, bands),
            "coverage": coverage, "partial": coverage < PARTIAL_BELOW, "categories": cats}


# ------------------------------------------------------------------ fundamental score
@dataclass
class FundamentalInputs:
    revenue: Optional[Sequence[float]] = None            # last 3-5 years, oldest first (Rs crore)
    pat: Optional[Sequence[float]] = None                 # profit after tax, same years
    ebitda_margin_pct: Optional[float] = None
    roe_pct: Optional[float] = None
    roce_pct: Optional[float] = None
    debt_to_equity: Optional[float] = None
    interest_coverage: Optional[float] = None
    cfo: Optional[float] = None                           # latest-year operating cash flow
    inventory_days: Optional[float] = None
    inventory_days_prev: Optional[float] = None
    business_quality_rating: Optional[float] = None       # 0-5, your judgement
    management_rating: Optional[float] = None             # 0-5
    promoter_holding_post_pct: Optional[float] = None
    promoter_pledge_pct: Optional[float] = None
    litigation_severity: Optional[float] = None           # 0 none ... 5 severe
    peer_ebitda_margin_pct: Optional[float] = None
    peer_roe_pct: Optional[float] = None
    peer_revenue_growth_pct: Optional[float] = None
    pe_ratio: Optional[float] = None
    peer_pe_ratio: Optional[float] = None
    ofs_pct: Optional[float] = None                       # share of the issue that is an offer for sale
    use_of_funds_rating: Optional[float] = None           # 0-5

# ------------------------------------------------------------------
# RHP EVIDENCE MAPPING — uses the existing FundamentalInputs
# ------------------------------------------------------------------

def _evidence_approved(fields: dict, key: str):
    """Return a field value only if evidence is verified and approved."""

    item = fields.get(key)

    if not isinstance(item, dict):
        return None

    if item.get("status") != "verified":
        return None

    if item.get("approved") is not True:
        return None

    return item.get("value")


def _finite_number(value) -> bool:

    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _approved_number(fields: dict, key: str):
    value = _evidence_approved(fields, key)

    return (
        float(value)
        if _finite_number(value)
        else None
    )


def _approved_series(
    fields: dict,
    key: str,
    warnings: List[str]
):
    """Read an approved oldest-to-newest financial series."""

    raw = _evidence_approved(fields, key)

    if raw is None:
        return None

    if not isinstance(raw, list) or not raw:
        warnings.append(f"{key}: invalid or empty financial series.")
        return None

    periods = []
    values = []
    years = []

    for row in raw:

        if not isinstance(row, dict):
            warnings.append(f"{key}: invalid financial row.")
            return None

        period = row.get("period")
        amount = row.get("amount")

        if not isinstance(period, str) or not period.strip():
            warnings.append(f"{key}: financial period is missing.")
            return None

        if not _finite_number(amount):
            warnings.append(f"{key}: invalid amount for {period}.")
            return None

        match = re.search(r"(?:19|20)\d{2}", period)

        if not match:
            warnings.append(
                f"{key}: unable to establish year order for {period}."
            )
            return None

        periods.append(period.strip())
        years.append(int(match.group()))
        values.append(float(amount))

    if len(set(periods)) != len(periods):
        warnings.append(f"{key}: duplicate financial periods.")
        return None

    if years == sorted(years, reverse=True) and len(years) > 1:
        orig_periods = list(periods)
        periods = list(reversed(periods))
        values = list(reversed(values))
        years = list(reversed(years))
        warnings.append(
            f"{key}: periods were reported newest-to-oldest ({', '.join(orig_periods)}). "
            f"Normalized into chronological order for scoring ({', '.join(periods)})."
        )
    elif years != sorted(years):
        warnings.append(
            f"{key}: ambiguous or non-chronological financial periods ({', '.join(periods)}). "
            "Review the original financial table."
        )
        return None

    return {
        "periods": periods,
        "values": values
    }


def _approved_amount(fields: dict, key: str):

    raw = _evidence_approved(fields, key)

    if not isinstance(raw, dict):
        return None

    amount = raw.get("amount")
    unit = raw.get("unit")

    if not _finite_number(amount):
        return None

    if not isinstance(unit, str) or not unit.strip():
        return None

    return {
        "amount": float(amount),
        "unit": unit.strip().casefold()
    }


def fundamental_inputs_from_evidence(
    fields: dict,
    manual_overrides: Optional[dict] = None
):
    """
    Map approved, source-backed RHP evidence into FundamentalInputs.

    Returns:
        (FundamentalInputs, warnings)

    Existing score_fundamental() remains the only scoring function.

    Manual overrides take precedence over extracted fields.
    """

    fields = fields or {}
    manual_overrides = manual_overrides or {}

    warnings = []
    values = {}

    # --------------------------------------------------------------
    # 1. Revenue and PAT — require matching reporting periods
    # --------------------------------------------------------------

    revenue_data = _approved_series(
        fields,
        "revenue",
        warnings
    )

    pat_data = _approved_series(
        fields,
        "pat",
        warnings
    )

    if revenue_data and pat_data:

        if revenue_data["periods"] != pat_data["periods"]:

            warnings.append(
                "Revenue and PAT reporting periods do not match. "
                "Both series have been excluded from automatic mapping."
            )

            revenue_data = None
            pat_data = None

    values["revenue"] = (
        revenue_data["values"]
        if revenue_data else None
    )

    values["pat"] = (
        pat_data["values"]
        if pat_data else None
    )

    # --------------------------------------------------------------
    # 2. Directly disclosed numerical fields
    # --------------------------------------------------------------

    direct_fields = [
        "ebitda_margin_pct",
        "roe_pct",
        "roce_pct",
        "debt_to_equity",
        "interest_coverage",
        "promoter_holding_post_pct",
        "promoter_pledge_pct",
        "peer_ebitda_margin_pct",
        "peer_roe_pct",
        "peer_revenue_growth_pct",
        "pe_ratio",
        "peer_pe_ratio",
        "ofs_pct",
    ]

    for field in direct_fields:

        values[field] = _approved_number(
            fields,
            field
        )

    # --------------------------------------------------------------
    # 3. EBITDA margin from matching EBITDA and revenue periods
    # --------------------------------------------------------------

    if values["ebitda_margin_pct"] is None:

        ebitda_data = _approved_series(
            fields,
            "ebitda",
            warnings
        )

        if revenue_data and ebitda_data:

            latest_period = revenue_data["periods"][-1]

            if ebitda_data["periods"][-1] == latest_period:

                revenue_latest = revenue_data["values"][-1]
                ebitda_latest = ebitda_data["values"][-1]

                if revenue_latest > 0:

                    values["ebitda_margin_pct"] = (
                        ebitda_latest / revenue_latest
                    ) * 100

            else:

                warnings.append(
                    "EBITDA and revenue periods do not match. "
                    "EBITDA margin was not calculated."
                )

    # --------------------------------------------------------------
    # 4. Debt/equity from matching borrowings and net worth
    # --------------------------------------------------------------

    if values["debt_to_equity"] is None:

        borrowing_data = _approved_series(
            fields,
            "total_borrowings",
            warnings
        )

        net_worth_data = _approved_series(
            fields,
            "net_worth",
            warnings
        )

        if borrowing_data and net_worth_data:

            period = borrowing_data["periods"][-1]

            if net_worth_data["periods"][-1] == period:

                borrowings = borrowing_data["values"][-1]
                net_worth = net_worth_data["values"][-1]

                if borrowings >= 0 and net_worth > 0:

                    values["debt_to_equity"] = (
                        borrowings / net_worth
                    )

            else:

                warnings.append(
                    "Borrowings and net worth periods do not match. "
                    "Debt/equity was not calculated."
                )

    # --------------------------------------------------------------
    # 5. Latest operating cash flow
    # --------------------------------------------------------------

    cfo_value = _evidence_approved(
        fields,
        "cfo"
    )

    if isinstance(cfo_value, list):

        cfo_data = _approved_series(
            fields,
            "cfo",
            warnings
        )

        if cfo_data:

            if pat_data:

                if (
                    cfo_data["periods"][-1]
                    == pat_data["periods"][-1]
                ):

                    values["cfo"] = cfo_data["values"][-1]

                else:

                    values["cfo"] = None

                    warnings.append(
                        "Latest CFO and PAT periods do not match. "
                        "CFO was not mapped."
                    )

            else:

                values["cfo"] = cfo_data["values"][-1]

        else:

            values["cfo"] = None

    elif _finite_number(cfo_value):

        values["cfo"] = float(cfo_value)

    else:

        values["cfo"] = None

    # --------------------------------------------------------------
    # 5b. Operating inventory days
    # --------------------------------------------------------------

    inv_value = _evidence_approved(
        fields,
        "inventory_days"
    )

    if isinstance(inv_value, list):
        inv_data = _approved_series(
            fields,
            "inventory_days",
            warnings
        )
        if inv_data and inv_data["values"]:
            values["inventory_days"] = inv_data["values"][-1]
            if len(inv_data["values"]) >= 2:
                values["inventory_days_prev"] = inv_data["values"][-2]
    elif _finite_number(inv_value):
        values["inventory_days"] = float(inv_value)

    # --------------------------------------------------------------
    # 6. OFS percentage from verified issue amounts
    # --------------------------------------------------------------

    if values["ofs_pct"] is None:

        fresh = _approved_amount(
            fields,
            "fresh_issue_amount"
        )

        ofs = _approved_amount(
            fields,
            "ofs_amount"
        )

        if fresh and ofs:

            if fresh["unit"] == ofs["unit"]:

                total = (
                    fresh["amount"] + ofs["amount"]
                )

                if total > 0 and fresh["amount"] >= 0 and ofs["amount"] >= 0:

                    values["ofs_pct"] = (
                        ofs["amount"] / total
                    ) * 100

            else:

                warnings.append(
                    "Fresh issue and OFS amount units differ. "
                    "OFS percentage was not calculated."
                )

    # --------------------------------------------------------------
    # 7. Manual judgement and manual corrections
    # --------------------------------------------------------------

    allowed_fields = set(
        FundamentalInputs.__dataclass_fields__
    )

    unknown_fields = set(manual_overrides) - allowed_fields

    if unknown_fields:

        warnings.append(
            "Unknown manual input fields ignored: "
            + ", ".join(sorted(unknown_fields))
        )

    for key, value in manual_overrides.items():

        if key in allowed_fields and value is not None:

            values[key] = value

    inputs = FundamentalInputs(**values)

    validation_errors = validate_fundamental_inputs(
        inputs
    )

    if validation_errors:

        raise ValueError(
            "Invalid fundamental inputs: "
            + "; ".join(validation_errors)
        )

    return inputs, warnings


# ------------------------------------------------------------------
# INPUT VALIDATION — existing scoring interface preserved
# ------------------------------------------------------------------

def validate_fundamental_inputs(
    inp: FundamentalInputs
) -> List[str]:

    errors = []

    scalar_fields = [
        "ebitda_margin_pct",
        "roe_pct",
        "roce_pct",
        "debt_to_equity",
        "interest_coverage",
        "cfo",
        "inventory_days",
        "inventory_days_prev",
        "business_quality_rating",
        "management_rating",
        "promoter_holding_post_pct",
        "promoter_pledge_pct",
        "litigation_severity",
        "peer_ebitda_margin_pct",
        "peer_roe_pct",
        "peer_revenue_growth_pct",
        "pe_ratio",
        "peer_pe_ratio",
        "ofs_pct",
        "use_of_funds_rating",
    ]

    for name in scalar_fields:

        value = getattr(inp, name)

        if value is None:
            continue

        if not _finite_number(value):

            errors.append(
                f"{name} must be a finite number or None."
            )

    # Financial series
    for name in ("revenue", "pat"):

        series = getattr(inp, name)

        if series is None:
            continue

        if isinstance(series, (str, bytes)):

            errors.append(
                f"{name} must be a numerical sequence."
            )

            continue

        try:
            items = list(series)
        except TypeError:

            errors.append(
                f"{name} must be a numerical sequence."
            )

            continue

        for index, value in enumerate(items):

            if not _finite_number(value):

                errors.append(
                    f"{name}[{index}] is not a finite number."
                )

        if name == "revenue":

            if any(
                _finite_number(v) and v < 0
                for v in items
            ):

                errors.append(
                    "Revenue cannot be negative."
                )

    if (
        inp.revenue is not None
        and inp.pat is not None
        and len(inp.revenue) != len(inp.pat)
    ):

        errors.append(
            "Revenue and PAT must cover matching financial periods."
        )

    # Percentages that cannot exceed 100.
    for name in (
        "promoter_holding_post_pct",
        "promoter_pledge_pct",
        "ofs_pct"
    ):

        value = getattr(inp, name)

        if _finite_number(value) and not 0 <= value <= 100:

            errors.append(
                f"{name} must be between 0 and 100."
            )

    # Existing subjective rating scale: 0-5.
    for name in (
        "business_quality_rating",
        "management_rating",
        "litigation_severity",
        "use_of_funds_rating"
    ):

        value = getattr(inp, name)

        if _finite_number(value) and not 0 <= value <= 5:

            errors.append(
                f"{name} must be between 0 and 5."
            )

    if (
        _finite_number(inp.debt_to_equity)
        and inp.debt_to_equity < 0
    ):

        errors.append(
            "debt_to_equity cannot be negative."
        )

    for name in ("pe_ratio", "peer_pe_ratio"):

        value = getattr(inp, name)

        if _finite_number(value) and value <= 0:

            errors.append(
                f"{name} must be greater than zero."
            )

    for name in ("inventory_days", "inventory_days_prev"):

        value = getattr(inp, name)

        if _finite_number(value) and value < 0:

            errors.append(
                f"{name} cannot be negative."
            )

    return errors

def score_fundamental(inp: FundamentalInputs) -> dict:
    validation_errors = validate_fundamental_inputs(inp)
    if validation_errors:
        raise ValueError(
            "Invalid fundamental inputs: "
            + "; ".join(validation_errors)
        )

    flags: List[str] = []
    rev, pat = _clean(inp.revenue), _clean(inp.pat)
    rc, pc = cagr(rev), cagr(pat)

    # growth
    s_rev = interp(rc, GROWTH_POINTS)
    s_pat = None
    if pat:
        if pat[-1] <= 0:
            s_pat = 0.0
            flags.append("Loss-making in the latest year.")
        elif pc is not None:
            s_pat = interp(pc, GROWTH_POINTS)
        elif len(pat) >= 2:
            s_pat = 0.5                                   # turned profitable
    growth = mean_available([s_rev, s_pat])
    profit_weak = (pc is not None and pc <= 2) or (len(pat) >= 2 and pat[-1] <= pat[-2])
    if rc is not None and rc >= 8 and pat and profit_weak:
        flags.append("Revenue is rising but profits are flat or falling.")

    # profitability and balance sheet
    profitability = mean_available([interp(inp.ebitda_margin_pct, [(0, 0), (8, .3), (15, .6), (25, 1)]),
                                    interp(inp.roe_pct, [(0, 0), (8, .3), (15, .7), (25, 1)]),
                                    interp(inp.roce_pct, [(0, 0), (8, .3), (15, .7), (25, 1)])])
    debt = mean_available([interp(inp.debt_to_equity, [(0, 1), (.5, .85), (1, .6), (2, .25), (3, 0)]),
                           interp(inp.interest_coverage, [(1, 0), (2, .3), (4, .7), (8, 1)])])

    # cash flow and working capital
    ratio, s_cfo, s_wc, inv_change = None, None, None, None
    if not _missing(inp.cfo):
        if pat and pat[-1] > 0:
            ratio = float(inp.cfo) / pat[-1]
            s_cfo = interp(ratio, [(0, 0), (.5, .4), (.8, .7), (1.0, 1)])
        elif pat:
            s_cfo = 0.5 if inp.cfo > 0 else 0.0
    if not _missing(inp.inventory_days) and not _missing(inp.inventory_days_prev) and inp.inventory_days_prev > 0:
        inv_change = (inp.inventory_days / inp.inventory_days_prev - 1.0) * 100.0
        s_wc = interp(inv_change, [(0, 1), (25, .5), (60, 0)])
    cashflow = _wmean([(0.7, s_cfo), (0.3, s_wc)])
    if ratio is not None and ratio < 0.5:
        flags.append("Operating cash flow is far below reported profit.")
    if not _missing(inp.debt_to_equity) and inp.debt_to_equity > 2 and \
            ((ratio is not None and ratio < 0.5) or (not _missing(inp.cfo) and inp.cfo <= 0)):
        flags.append("High debt together with weak cash flow.")
    g_last = (rev[-1] / rev[-2] - 1.0) * 100.0 if len(rev) >= 2 and rev[-2] > 0 else None
    if inv_change is not None and inv_change > 25 and g_last is not None and g_last < 10:
        flags.append("Inventory is building up faster than sales.")

    # promoter and management (litigation counts here)
    s_lit = None if _missing(inp.litigation_severity) else 1.0 - _rating(inp.litigation_severity)
    promoter = _wmean([(0.50, _rating(inp.management_rating)),
                       (0.15, interp(inp.promoter_holding_post_pct, [(25, .3), (50, .7), (75, 1)])),
                       (0.20, interp(inp.promoter_pledge_pct, [(0, 1), (10, .6), (30, .2), (50, 0)])),
                       (0.15, s_lit)])
    if not _missing(inp.promoter_pledge_pct) and inp.promoter_pledge_pct > 10:
        flags.append("Promoter shares are pledged.")
    if not _missing(inp.litigation_severity) and inp.litigation_severity >= 4:
        flags.append("Serious litigation or regulatory issues.")

    # peers, valuation, structure
    peers = mean_available([interp(d, [(-10, 0), (0, .6), (10, 1)]) for d in
                            (_diff(inp.ebitda_margin_pct, inp.peer_ebitda_margin_pct),
                             _diff(inp.roe_pct, inp.peer_roe_pct), _diff(rc, inp.peer_revenue_growth_pct))])
    premium = None
    if not _missing(inp.pe_ratio) and not _missing(inp.peer_pe_ratio) and inp.pe_ratio > 0 and inp.peer_pe_ratio > 0:
        premium = (inp.pe_ratio / inp.peer_pe_ratio - 1.0) * 100.0
    valuation = interp(premium, [(-20, 1), (0, .7), (20, .4), (50, .1), (80, 0)])
    if premium is not None and premium > 50:
        flags.append("Valuation is well above listed peers.")
    structure = mean_available([interp(inp.ofs_pct, [(0, 1), (30, .8), (60, .4), (100, .1)]),
                                _rating(inp.use_of_funds_rating)])
    if not _missing(inp.ofs_pct) and inp.ofs_pct > 60:
        flags.append("Mostly an offer for sale: existing holders are selling.")

    res = _combine({"Business quality": _rating(inp.business_quality_rating), "Revenue and profit growth": growth,
                    "Profitability": profitability, "Debt and balance sheet": debt,
                    "Cash flow and working capital": cashflow, "Promoter and management": promoter,
                    "Peer comparison": peers, "Valuation": valuation, "IPO structure and use of funds": structure},
                   FUNDAMENTAL_WEIGHTS, FUNDAMENTAL_BANDS)
    res["red_flags"] = flags
    res["metrics"] = {"revenue_cagr_pct": rc, "pat_cagr_pct": pc, "cfo_to_pat": ratio, "pe_premium_pct": premium}
    return res

# ------------------------------------------------------------------ listing score
@dataclass
class ListingInputs:
    gmp_pct: Optional[float] = None                       # final GMP as % of the issue price
    qib_sub: Optional[float] = None                       # times subscribed
    total_sub: Optional[float] = None
    nifty_ret_20d: Optional[float] = None                 # Nifty 50 return over the previous 20 trading days, %
    pe_premium_pct: Optional[float] = None                # IPO P/E premium to listed peers, %
    sector_sentiment_rating: Optional[float] = None       # 0-5
    issue_size_cr: Optional[float] = None


def score_listing(inp: ListingInputs) -> dict:
    res = _combine({
        "GMP": interp(inp.gmp_pct, [(-5, 0), (0, .1), (10, .4), (25, .75), (50, 1)]),
        "QIB subscription": interp(inp.qib_sub, [(0, 0), (1, .1), (5, .4), (20, .75), (80, 1)]),
        "Total subscription": interp(inp.total_sub, [(0, 0), (1, .1), (3, .35), (10, .65), (50, .9), (100, 1)]),
        "Market sentiment": interp(inp.nifty_ret_20d, [(-6, 0), (0, .5), (6, 1)]),
        "IPO valuation": interp(inp.pe_premium_pct, [(-10, 1), (0, .75), (20, .4), (50, .1), (80, 0)]),
        "Sector sentiment": _rating(inp.sector_sentiment_rating),
        "Issue size and liquidity": interp(inp.issue_size_cr, [(0, .9), (1000, .8), (2500, .5), (5000, .3)]),
    }, LISTING_WEIGHTS, LISTING_BANDS)
    res["red_flags"] = []
    return res